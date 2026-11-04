import re
import secrets
import hashlib
import hmac
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional
from abc import ABC, abstractmethod
import logging
import httpx

from backend.app.core.config import settings

logger = logging.getLogger("atdesk.sms_service")

class SmsDeliveryResult:
    def __init__(self, success: bool, message_id: str, status: str, provider: str, details: Optional[str] = None):
        self.success = success
        self.message_id = message_id
        self.status = status  # DELIVERED, SUBMITTED, FAILED
        self.provider = provider
        self.details = details

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "message_id": self.message_id,
            "status": self.status,
            "provider": self.provider,
            "details": self.details
        }

class SmsProvider(ABC):
    @abstractmethod
    def send_sms(self, phone: str, otp_code: str) -> SmsDeliveryResult:
        pass

class GupshupSmsProvider(SmsProvider):
    """
    Gupshup Enterprise Indian SMS Provider Adapter with DLT Scrubbing.
    Connects to official Gupshup Enterprise REST Gateway API.
    """
    def send_sms(self, phone: str, otp_code: str) -> SmsDeliveryResult:
        if not settings.SMS_API_KEY and not (settings.SMS_GUPSHUP_USERID and settings.SMS_GUPSHUP_PASSWORD):
            logger.error("[Gupshup DLT] Missing credentials: SMS_API_KEY or SMS_GUPSHUP_USERID/PASSWORD required.")
            return SmsDeliveryResult(
                success=False,
                message_id="",
                status="FAILED",
                provider="GUPSHUP",
                details="Gupshup credentials not configured"
            )

        # TRAI DLT approved template format:
        # {#var#} is your verification code for AtDesk by The Sorted Club. Valid for 5 minutes. Do not share this OTP with anyone.
        message_body = (
            f"{otp_code} is your verification code for AtDesk by The Sorted Club. "
            f"Valid for 5 minutes. Do not share this OTP with anyone."
        )

        url = "https://enterprise.smsgupshup.com/GatewayAPI/rest"
        params = {
            "method": "SendMessage",
            "send_to": f"91{phone[-10:]}",
            "msg": message_body,
            "msg_type": "TEXT",
            "userid": settings.SMS_GUPSHUP_USERID or settings.SMS_API_KEY,
            "password": settings.SMS_GUPSHUP_PASSWORD or settings.SMS_API_KEY,
            "auth_scheme": "plain",
            "v": "1.1",
            "format": "json",
            "principalEntityId": settings.SMS_DLT_PE_ID,
            "dltTemplateId": settings.SMS_DLT_TEMPLATE_ID,
        }

        try:
            with httpx.Client(timeout=8.0) as client:
                response = client.post(url, data=params)
                if response.status_code == 200:
                    try:
                        res_json = response.json()
                        resp_obj = res_json.get("response", {})
                        if resp_obj.get("status") == "success":
                            msg_id = resp_obj.get("id", f"gup_{secrets.token_hex(6)}")
                            logger.info(f"[Gupshup DLT] Accepted SMS to +91-XXXXX{phone[-5:]}. Message ID: {msg_id}")
                            return SmsDeliveryResult(
                                success=True,
                                message_id=msg_id,
                                status="DELIVERED",
                                provider="GUPSHUP",
                                details="Gupshup DLT submission accepted"
                            )
                        else:
                            details = resp_obj.get("details", response.text)
                            logger.warning(f"[Gupshup DLT] Provider rejected message: {details}")
                            return SmsDeliveryResult(
                                success=False,
                                message_id="",
                                status="FAILED",
                                provider="GUPSHUP",
                                details=f"Gupshup rejection: {details}"
                            )
                    except Exception:
                        if "success" in response.text.lower():
                            msg_id = f"gup_{secrets.token_hex(6)}"
                            return SmsDeliveryResult(
                                success=True,
                                message_id=msg_id,
                                status="DELIVERED",
                                provider="GUPSHUP",
                                details="Gupshup submission accepted"
                            )
                        return SmsDeliveryResult(
                            success=False,
                            message_id="",
                            status="FAILED",
                            provider="GUPSHUP",
                            details=f"Gupshup unexpected response: {response.text[:200]}"
                        )
                else:
                    logger.error(f"[Gupshup DLT] HTTP error {response.status_code}: {response.text[:200]}")
                    return SmsDeliveryResult(
                        success=False,
                        message_id="",
                        status="FAILED",
                        provider="GUPSHUP",
                        details=f"HTTP {response.status_code}: {response.text[:200]}"
                    )
        except Exception as exc:
            logger.error(f"[Gupshup DLT] Connection exception: {exc}")
            return SmsDeliveryResult(
                success=False,
                message_id="",
                status="FAILED",
                provider="GUPSHUP",
                details=f"Connection failure: {str(exc)}"
            )

class Msg91SmsProvider(SmsProvider):
    """
    MSG91 Indian SMS Provider Adapter with Flow & DLT API.
    Connects to official MSG91 OTP API (https://control.msg91.com/api/v5/otp).
    """
    def send_sms(self, phone: str, otp_code: str) -> SmsDeliveryResult:
        if not settings.SMS_API_KEY:
            logger.error("[MSG91 DLT] Missing SMS_API_KEY")
            return SmsDeliveryResult(
                success=False,
                message_id="",
                status="FAILED",
                provider="MSG91",
                details="MSG91 SMS_API_KEY not configured"
            )

        url = "https://control.msg91.com/api/v5/otp"
        headers = {
            "authkey": settings.SMS_API_KEY,
            "content-type": "application/json"
        }
        payload = {
            "template_id": settings.SMS_DLT_TEMPLATE_ID,
            "mobile": f"91{phone[-10:]}",
            "otp": otp_code
        }

        try:
            with httpx.Client(timeout=8.0) as client:
                response = client.post(url, json=payload, headers=headers)
                if response.status_code == 200:
                    data = response.json()
                    if data.get("type") == "success":
                        msg_id = data.get("message_id", f"msg91_{secrets.token_hex(6)}")
                        logger.info(f"[MSG91 DLT] Accepted OTP to +91-XXXXX{phone[-5:]}. Message ID: {msg_id}")
                        return SmsDeliveryResult(
                            success=True,
                            message_id=msg_id,
                            status="DELIVERED",
                            provider="MSG91",
                            details="MSG91 OTP accepted"
                        )
                    else:
                        details = data.get("message", "Rejected by provider")
                        logger.warning(f"[MSG91 DLT] Rejected: {details}")
                        return SmsDeliveryResult(
                            success=False,
                            message_id="",
                            status="FAILED",
                            provider="MSG91",
                            details=f"MSG91 rejection: {details}"
                        )
                else:
                    return SmsDeliveryResult(
                        success=False,
                        message_id="",
                        status="FAILED",
                        provider="MSG91",
                        details=f"HTTP {response.status_code}: {response.text[:200]}"
                    )
        except Exception as exc:
            logger.error(f"[MSG91 DLT] Connection exception: {exc}")
            return SmsDeliveryResult(
                success=False,
                message_id="",
                status="FAILED",
                provider="MSG91",
                details=f"Connection failure: {str(exc)}"
            )

class StagingMockSmsProvider(SmsProvider):
    """
    Mock SMS Adapter strictly for automated testing and local staging.
    FORBIDDEN in production environment.
    """
    def send_sms(self, phone: str, otp_code: str) -> SmsDeliveryResult:
        if settings.ENVIRONMENT.lower() in ["production", "prod"]:
            logger.critical("[SECURITY] Attempted to use Mock SMS Provider in PRODUCTION environment!")
            return SmsDeliveryResult(
                success=False,
                message_id="",
                status="FAILED",
                provider="MOCK_FORBIDDEN",
                details="Mock SMS provider is strictly forbidden in production mode"
            )

        logger.info(f"[Test Mock SMS] Generated OTP for +91-XXXXX{phone[-5:]} with template {settings.SMS_DLT_TEMPLATE_ID}")
        message_id = f"test_mock_{secrets.token_hex(6)}"
        return SmsDeliveryResult(
            success=True,
            message_id=message_id,
            status="DELIVERED",
            provider="TEST_MOCK",
            details=f"Mock SMS accepted for local/testing. Template ID: {settings.SMS_DLT_TEMPLATE_ID}"
        )

class SmsService:
    """
    Central SMS & OTP Security Service.
    Enforces:
    - Indian 10-digit mobile number validation (+91 or 10 digits starting 6-9)
    - Cryptographically random 6-digit OTP generation
    - 60-second resend cooldown
    - 5-minute OTP validity
    - Maximum 3 verification attempts before 15-minute phone lockout
    - Hourly rate limiting (max 5 OTP requests per hour per phone)
    - Zero exposure of production OTPs in responses or logs
    """
    _otp_store: Dict[str, Dict[str, Any]] = {}
    _request_history: Dict[str, list] = {}  # phone -> list of request timestamps
    _lockouts: Dict[str, datetime] = {}  # phone -> lockout expiry

    @classmethod
    def _normalize_phone(cls, phone: str) -> str:
        digits = re.sub(r"\D", "", phone)
        if digits.startswith("91") and len(digits) == 12:
            digits = digits[2:]
        if len(digits) != 10 or not digits[0] in "6789":
            raise ValueError(f"Invalid Indian mobile number '{phone}'. Must be a valid 10-digit number starting with 6, 7, 8, or 9.")
        return digits

    @classmethod
    def _get_provider(cls) -> SmsProvider:
        provider_name = settings.SMS_PROVIDER.upper().strip()
        if settings.ENVIRONMENT.lower() in ["production", "prod"]:
            if provider_name == "GUPSHUP":
                return GupshupSmsProvider()
            elif provider_name == "MSG91":
                return Msg91SmsProvider()
            else:
                logger.error(f"[SECURITY] Invalid production SMS_PROVIDER: {provider_name}")
                raise ValueError(f"Production SMS_PROVIDER must be 'GUPSHUP' or 'MSG91'. Found: {provider_name}")

        # Non-production environments
        if provider_name == "GUPSHUP":
            return GupshupSmsProvider()
        elif provider_name == "MSG91":
            return Msg91SmsProvider()
        else:
            return StagingMockSmsProvider()

    @classmethod
    def generate_and_send_otp(cls, raw_phone: str) -> Dict[str, Any]:
        phone = cls._normalize_phone(raw_phone)
        now = datetime.now(timezone.utc)

        # 1. Check phone lockout
        lockout_expiry = cls._lockouts.get(phone)
        if lockout_expiry and now < lockout_expiry:
            remaining_mins = max(1, int((lockout_expiry - now).total_seconds() / 60))
            return {
                "success": False,
                "error": "LOCKED_OUT",
                "message": f"Account temporarily locked due to excessive failed attempts. Please retry in {remaining_mins} minutes."
            }

        # 2. Check 60-second resend cooldown
        existing = cls._otp_store.get(phone)
        if existing:
            last_sent = existing.get("created_at")
            if last_sent:
                elapsed = (now - last_sent).total_seconds()
                if elapsed < settings.OTP_RESEND_COOLDOWN_SECONDS:
                    wait_time = int(settings.OTP_RESEND_COOLDOWN_SECONDS - elapsed)
                    return {
                        "success": False,
                        "error": "COOLDOWN_ACTIVE",
                        "message": f"Please wait {wait_time} seconds before requesting a new OTP.",
                        "cooldown_remaining": wait_time
                    }

        # 3. Check hourly rate limit (max 5 requests per hour)
        history = cls._request_history.setdefault(phone, [])
        one_hour_ago = now - timedelta(hours=1)
        history = [t for t in history if t > one_hour_ago]
        if len(history) >= 5:
            return {
                "success": False,
                "error": "RATE_LIMIT_EXCEEDED",
                "message": "Maximum OTP request limit reached (5 requests/hour). Please try again later."
            }
        history.append(now)
        cls._request_history[phone] = history

        # 4. Generate secure 6-digit OTP
        otp_code = f"{secrets.randbelow(900000) + 100000}"
        otp_hash = hashlib.sha256(otp_code.encode("utf-8")).hexdigest()

        # 5. Store record
        cls._otp_store[phone] = {
            "otp_hash": otp_hash,
            "created_at": now,
            "expires_at": now + timedelta(seconds=settings.OTP_VALIDITY_SECONDS),
            "attempts": 0,
            "is_verified": False,
        }

        # 6. Dispatch through configured provider
        provider = cls._get_provider()
        delivery = provider.send_sms(phone, otp_code)

        masked_phone = f"+91-XXXXX{phone[-5:]}"

        if not delivery.success:
            logger.error(f"[SMS OTP] Delivery failed to {masked_phone} via {delivery.provider}: {delivery.details}")
            return {
                "success": False,
                "error": "SMS_DELIVERY_FAILED",
                "message": f"Failed to send SMS OTP via {delivery.provider}. Please verify connectivity or retry later.",
                "delivery_status": delivery.status,
                "details": delivery.details
            }

        response_data = {
            "success": True,
            "message": f"OTP successfully sent to {masked_phone} via {delivery.provider}.",
            "delivery_status": delivery.status,
            "message_id": delivery.message_id,
            "dlt_template_id": settings.SMS_DLT_TEMPLATE_ID,
            "cooldown_seconds": settings.OTP_RESEND_COOLDOWN_SECONDS,
            "expires_in_seconds": settings.OTP_VALIDITY_SECONDS
        }

        # Staging test support: ONLY in non-production local/test environments
        if settings.ENVIRONMENT.lower() not in ["production", "prod"]:
            if "test" in settings.ENVIRONMENT.lower() or "staging" in settings.ENVIRONMENT.lower() or settings.SMS_PROVIDER == "TEST_MOCK":
                response_data["staging_test_otp"] = otp_code

        return response_data

    @classmethod
    def verify_otp(cls, raw_phone: str, entered_otp: str) -> Dict[str, Any]:
        phone = cls._normalize_phone(raw_phone)
        now = datetime.now(timezone.utc)

        # 1. Check lockout
        lockout_expiry = cls._lockouts.get(phone)
        if lockout_expiry and now < lockout_expiry:
            remaining_mins = max(1, int((lockout_expiry - now).total_seconds() / 60))
            return {
                "success": False,
                "error": "LOCKED_OUT",
                "message": f"Account temporarily locked due to excessive failed attempts. Please retry in {remaining_mins} minutes."
            }

        # 2. Check record exists
        record = cls._otp_store.get(phone)
        if not record:
            return {
                "success": False,
                "error": "NO_OTP_FOUND",
                "message": "No active OTP request found for this phone number. Please request an OTP first."
            }

        # 3. Check expiration
        if now > record["expires_at"]:
            cls._otp_store.pop(phone, None)
            return {
                "success": False,
                "error": "EXPIRED",
                "message": "OTP has expired (5-minute validity). Please request a new OTP."
            }

        # 4. Check already verified
        if record.get("is_verified"):
            return {
                "success": False,
                "error": "ALREADY_USED",
                "message": "This OTP has already been verified and used."
            }

        # 5. Check maximum attempts
        if record["attempts"] >= settings.OTP_MAX_ATTEMPTS:
            cls._otp_store.pop(phone, None)
            cls._lockouts[phone] = now + timedelta(minutes=15)
            logger.warning(f"[Security Alert] Phone {phone} locked out for 15 minutes due to 3 consecutive failed OTP attempts.")
            return {
                "success": False,
                "error": "LOCKED_OUT",
                "message": "Maximum verification attempts exceeded (3 attempts). Phone locked for 15 minutes for security."
            }

        # 6. Verify hash
        entered_hash = hashlib.sha256(entered_otp.strip().encode("utf-8")).hexdigest()
        if not hmac.compare_digest(record["otp_hash"], entered_hash):
            record["attempts"] += 1
            remaining = settings.OTP_MAX_ATTEMPTS - record["attempts"]
            if remaining <= 0:
                cls._otp_store.pop(phone, None)
                cls._lockouts[phone] = now + timedelta(minutes=15)
                logger.warning(f"[Security Alert] Phone {phone} locked out for 15 minutes due to {settings.OTP_MAX_ATTEMPTS} consecutive failed OTP attempts.")
                return {
                    "success": False,
                    "error": "MAX_ATTEMPTS_EXCEEDED",
                    "message": "Maximum verification attempts exceeded (3 attempts). Phone locked for 15 minutes for security."
                }
            return {
                "success": False,
                "error": "INVALID_OTP",
                "message": f"Incorrect verification code. {remaining} attempt(s) remaining.",
                "attempts_remaining": remaining
            }

        # 7. Success: Mark verified & pop
        record["is_verified"] = True
        cls._otp_store.pop(phone, None)
        cls._lockouts.pop(phone, None)
        return {
            "success": True,
            "message": "Phone number successfully verified."
        }
