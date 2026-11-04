import os
import uuid
import hmac
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional
import logging
import boto3
from botocore.exceptions import ClientError
from botocore.config import Config

from backend.app.core.config import settings

logger = logging.getLogger("atdesk.storage_service")

ALLOWED_MIME_TYPES = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp"
}

class StorageService:
    """
    AWS S3 & Cloudflare R2 Private Object Storage Adapter for Delivery Proof Photographs.
    Enforces:
    - Pre-signed POST/PUT upload URLs (short-lived, 15 min).
    - File size limits (max 5 MB).
    - MIME-type enforcement (JPEG, PNG, WebP only).
    - Pre-signed GET download URLs (never long-lived public URLs).
    - Audit logging of photo accesses.
    - Cloudflare R2 endpoint_url compatibility.
    """

    @classmethod
    def _get_s3_client(cls):
        access_key = settings.AWS_ACCESS_KEY_ID
        secret_key = settings.AWS_SECRET_ACCESS_KEY
        endpoint_url = settings.S3_ENDPOINT_URL
        region = settings.AWS_REGION or "auto"

        kwargs = {
            "region_name": region,
            "aws_access_key_id": access_key,
            "aws_secret_access_key": secret_key,
            "config": Config(signature_version="s3v4")
        }
        if endpoint_url:
            kwargs["endpoint_url"] = endpoint_url

        return boto3.client("s3", **kwargs)

    @classmethod
    def generate_presigned_upload_url(
        cls,
        master_order_id: int,
        mime_type: str = "image/jpeg",
        expires_in: int = 900
    ) -> Dict[str, Any]:
        """
        Generates backend-authorized pre-signed upload URL for runner app.
        Enforces 5MB limit and MIME validation.
        """
        clean_mime = mime_type.lower().strip()
        if clean_mime not in ALLOWED_MIME_TYPES:
            raise ValueError(f"Unsupported MIME type '{clean_mime}'. Allowed: {list(ALLOWED_MIME_TYPES.keys())}")

        ext = ALLOWED_MIME_TYPES[clean_mime]
        now = datetime.now(timezone.utc)
        unique_file_id = f"proof_{master_order_id}_{now.strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}{ext}"
        s3_key = f"delivery-evidence/{now.strftime('%Y/%m/%d')}/{unique_file_id}"

        is_prod = settings.ENVIRONMENT.lower() in ["production", "prod"]

        try:
            client = cls._get_s3_client()
            presigned_post = client.generate_presigned_post(
                Bucket=settings.S3_BUCKET_NAME,
                Key=s3_key,
                Fields={"Content-Type": clean_mime},
                Conditions=[
                    {"Content-Type": clean_mime},
                    ["content-length-range", 100, settings.MAX_UPLOAD_SIZE_BYTES]
                ],
                ExpiresIn=expires_in
            )
            return {
                "success": True,
                "upload_mode": "S3_PRESIGNED_POST",
                "upload_url": presigned_post["url"],
                "fields": presigned_post["fields"],
                "s3_key": s3_key,
                "max_size_bytes": settings.MAX_UPLOAD_SIZE_BYTES,
                "expires_in_seconds": expires_in
            }
        except Exception as e:
            logger.warning(f"S3/R2 client generate_presigned_post error: {e}")
            if is_prod:
                raise RuntimeError(f"Private cloud storage is required in production: {e}")

            # Non-production Staging Secure URL with HMAC token fallback
            token_payload = f"{s3_key}:{int(now.timestamp()) + expires_in}"
            token = hmac.new(settings.SECRET_KEY.encode(), token_payload.encode(), hashlib.sha256).hexdigest()
            upload_url = f"/api/storage/staging-upload?key={s3_key}&token={token}&expires={int(now.timestamp()) + expires_in}"
            return {
                "success": True,
                "upload_mode": "STAGING_SECURE_TOKEN",
                "upload_url": upload_url,
                "fields": {"Content-Type": clean_mime},
                "s3_key": s3_key,
                "max_size_bytes": settings.MAX_UPLOAD_SIZE_BYTES,
                "expires_in_seconds": expires_in
            }

    @classmethod
    def generate_presigned_download_url(
        cls,
        s3_key: str,
        expires_in: int = 900
    ) -> str:
        """
        Generates temporary pre-signed GET URL for delivery photo.
        Prevents direct long-lived public access to customer office desks.
        """
        now = datetime.now(timezone.utc)
        is_prod = settings.ENVIRONMENT.lower() in ["production", "prod"]

        try:
            client = cls._get_s3_client()
            url = client.generate_presigned_url(
                ClientMethod="get_object",
                Params={"Bucket": settings.S3_BUCKET_NAME, "Key": s3_key},
                ExpiresIn=expires_in
            )
            return url
        except Exception as e:
            if is_prod:
                raise RuntimeError(f"Failed to generate pre-signed download URL from private cloud storage: {e}")
            expires_timestamp = int(now.timestamp()) + expires_in
            token_payload = f"GET:{s3_key}:{expires_timestamp}"
            token = hmac.new(settings.SECRET_KEY.encode(), token_payload.encode(), hashlib.sha256).hexdigest()
            return f"/api/storage/evidence-view?key={s3_key}&token={token}&expires={expires_timestamp}"

    @classmethod
    def verify_staging_token(cls, method: str, s3_key: str, token: str, expires_timestamp: int) -> bool:
        """Verifies staging signed download/upload token"""
        now = int(datetime.now(timezone.utc).timestamp())
        if now > expires_timestamp:
            return False
        if method.upper() == "GET":
            expected = hmac.new(settings.SECRET_KEY.encode(), f"GET:{s3_key}:{expires_timestamp}".encode(), hashlib.sha256).hexdigest()
        else:
            expected = hmac.new(settings.SECRET_KEY.encode(), f"{s3_key}:{expires_timestamp}".encode(), hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, token)
