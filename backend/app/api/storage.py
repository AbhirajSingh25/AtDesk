from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Response
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone
from typing import Dict, Any, Optional
import os

from backend.app.core.database import get_db
from backend.app.core.security import get_current_user_optional, require_roles
from backend.app.models.models import User, UserRole, AuditLog
from backend.app.services.storage_service import StorageService

router = APIRouter(prefix="/storage", tags=["Private Storage"])

LOCAL_STORAGE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "storage_vault")
os.makedirs(LOCAL_STORAGE_DIR, exist_ok=True)

@router.post("/presigned-upload-url")
async def get_presigned_upload_url(
    payload: Dict[str, Any],
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate short-lived pre-signed URL for runner to upload delivery proof photo.
    Restricted to max 5MB and JPEG/PNG/WebP.
    """
    master_order_id = payload.get("master_order_id")
    mime_type = payload.get("mime_type", "image/jpeg")

    if not master_order_id:
        raise HTTPException(status_code=400, detail="master_order_id is required")

    try:
        result = StorageService.generate_presigned_upload_url(
            master_order_id=int(master_order_id),
            mime_type=mime_type
        )
        return result
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))

@router.get("/presigned-download-url")
async def get_presigned_download_url(
    s3_key: str = Query(..., description="S3 Key or Storage Path of evidence"),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate temporary pre-signed URL for viewing delivery photo.
    Records access in AuditLog.
    """
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required to view delivery evidence")

    download_url = StorageService.generate_presigned_download_url(s3_key=s3_key)

    # Record Audit Log
    audit = AuditLog(
        user_id=str(current_user.id),
        role=current_user.role.value,
        action="DELIVERY_PHOTO_ACCESSED",
        target_entity="delivery_proofs",
        target_id=s3_key,
        details=f"User {current_user.full_name} generated temporary viewing URL for {s3_key}"
    )
    db.add(audit)
    await db.commit()

    return {
        "success": True,
        "download_url": download_url,
        "expires_in_seconds": 900
    }

@router.post("/staging-upload")
async def staging_upload(
    key: str = Query(...),
    token: str = Query(...),
    expires: int = Query(...),
    file: UploadFile = File(...)
):
    """Secure upload receiver for staging environments with token verification"""
    is_valid = StorageService.verify_staging_token("POST", key, token, expires)
    if not is_valid:
        raise HTTPException(status_code=403, detail="Invalid or expired staging upload token")

    content = await file.read()
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File size exceeds 5MB limit")

    safe_filename = key.replace("/", "_")
    target_path = os.path.join(LOCAL_STORAGE_DIR, safe_filename)
    with open(target_path, "wb") as f:
        f.write(content)

    return {"success": True, "s3_key": key, "size": len(content)}

@router.get("/evidence-view")
async def staging_view(
    key: str = Query(...),
    token: str = Query(...),
    expires: int = Query(...)
):
    """Secure evidence view endpoint for staging environments with token verification"""
    is_valid = StorageService.verify_staging_token("GET", key, token, expires)
    if not is_valid:
        raise HTTPException(status_code=403, detail="Invalid or expired staging viewing token")

    safe_filename = key.replace("/", "_")
    target_path = os.path.join(LOCAL_STORAGE_DIR, safe_filename)
    if not os.path.exists(target_path):
        # Return fallback placeholder bytes
        return Response(content=b"SIMULATED_PRIVATE_IMAGE_BYTES", media_type="image/jpeg")

    with open(target_path, "rb") as f:
        data = f.read()
    return Response(content=data, media_type="image/jpeg")

