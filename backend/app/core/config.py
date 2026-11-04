import os
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_DEV_SECRET = "atdesk_dev_insecure_secret_key_change_in_production_2026"

class Settings(BaseSettings):
    PROJECT_NAME: str = "AtDesk"
    VERSION: str = "2.1.0"
    PARENT_BRAND: str = "The Sorted Club"
    LAUNCH_LOCATION: str = "JMD Megapolis, Sector 48, Gurugram"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")  # development | staging | production
    
    # 1. Managed PostgreSQL Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        "postgresql+asyncpg://postgres:atdesk_staging@127.0.0.1:5433/atdesk_staging"
    )
    
    # 2. Security & JWT
    SECRET_KEY: str = os.getenv("SECRET_KEY", DEFAULT_DEV_SECRET)
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "43200"))  # 30 days
    
    # 3. Operational Policies
    FLAT_DELIVERY_FEE: float = 25.00  # Flat ₹25 delivery fee across all concourse shops
    CANCELLATION_WINDOW_SECONDS: int = 120  # Strict 2-minute server-authoritative window
    MIN_SHOP_PREPAID_ALERT_THRESHOLD: float = 1500.00
    SHOP_ACCEPTANCE_TIMEOUT_SECONDS: int = 180  # 3 minutes before auto-escalation
    
    # 4. Indian DLT SMS Configuration (Canonical Variable Names)
    SMS_PROVIDER: str = os.getenv("SMS_PROVIDER", "TEST_MOCK")  # GUPSHUP | MSG91 | TEST_MOCK
    SMS_API_KEY: str = os.getenv("SMS_API_KEY", "")
    SMS_SENDER_ID: str = os.getenv("SMS_SENDER_ID", "SORTED")
    SMS_DLT_PE_ID: str = os.getenv("SMS_DLT_PE_ID", "1701159876543210987")  # TRAI Principal Entity ID
    SMS_DLT_TEMPLATE_ID: str = os.getenv("SMS_DLT_TEMPLATE_ID", "1707161234567890123")  # Registered Content Template ID
    SMS_GUPSHUP_USERID: Optional[str] = os.getenv("SMS_GUPSHUP_USERID")
    SMS_GUPSHUP_PASSWORD: Optional[str] = os.getenv("SMS_GUPSHUP_PASSWORD")
    OTP_VALIDITY_SECONDS: int = 300  # 5 minutes
    OTP_RESEND_COOLDOWN_SECONDS: int = 60  # Minimum 60s cooldown
    OTP_MAX_ATTEMPTS: int = 3  # Max 3 attempts before lockout
    
    # 5. Razorpay Gateway (Canonical Variable Names)
    RAZORPAY_KEY_ID: str = os.getenv("RAZORPAY_KEY_ID", "rzp_test_AtDeskDemo2026")
    RAZORPAY_KEY_SECRET: str = os.getenv("RAZORPAY_KEY_SECRET", "rzp_test_secret_AtDeskSecurityKey")
    RAZORPAY_WEBHOOK_SECRET: str = os.getenv("RAZORPAY_WEBHOOK_SECRET", "atdesk_razorpay_webhook_secret_key_2026")
    
    # 6. Private Cloud Storage (AWS S3 & Cloudflare R2 Unified)
    STORAGE_BACKEND: str = os.getenv("STORAGE_BACKEND", "S3_PRIVATE")  # S3_PRIVATE | CLOUDFLARE_R2 | LOCAL_ENCRYPTED
    S3_BUCKET_NAME: str = os.getenv("S3_BUCKET_NAME", "atdesk-delivery-proofs-jmd-private")
    S3_ENDPOINT_URL: Optional[str] = os.getenv("S3_ENDPOINT_URL")  # Cloudflare R2 endpoint (e.g. https://<id>.r2.cloudflarestorage.com)
    AWS_REGION: str = os.getenv("AWS_REGION", "ap-south-1")  # Mumbai Region
    AWS_ACCESS_KEY_ID: str = os.getenv("AWS_ACCESS_KEY_ID") or os.getenv("S3_ACCESS_KEY", "mock_aws_access_key_atdesk")
    AWS_SECRET_ACCESS_KEY: str = os.getenv("AWS_SECRET_ACCESS_KEY") or os.getenv("S3_SECRET_KEY", "mock_aws_secret_key_atdesk")
    S3_PRESIGNED_EXPIRATION_SECONDS: int = 900  # 15 minutes max lifetime for pre-signed URLs
    MAX_UPLOAD_SIZE_BYTES: int = 5 * 1024 * 1024  # 5 MB max
    
    # 7. Firebase Cloud Messaging (FCM)
    FCM_SERVER_KEY: Optional[str] = os.getenv("FCM_SERVER_KEY")
    FCM_PROJECT_ID: str = os.getenv("FCM_PROJECT_ID", "atdesk-notifications-pilot")
    FIREBASE_CREDENTIALS_JSON: Optional[str] = os.getenv("FIREBASE_CREDENTIALS_JSON")
    
    # 8. JMD Megapolis Configuration
    JMD_TOWERS: List[str] = ["Tower A", "Tower B", "Tower C", "Tower D"]
    JMD_FLOORS: List[int] = list(range(1, 15))
    JMD_MEGAPOLIS_LATITUDE: float = 28.4162
    JMD_MEGAPOLIS_LONGITUDE: float = 77.0425
    
    # 9. Configurable CORS Approved Origins
    ALLOWED_ORIGINS: Optional[str] = os.getenv("ALLOWED_ORIGINS") or os.getenv("CORS_ORIGINS")

    @property
    def cors_origins(self) -> List[str]:
        default_origins = [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:8000",
            "http://127.0.0.1:8000",
            "capacitor://localhost",
            "http://localhost",
            "https://localhost",
            "https://atdesk.thesortedclub.com",
            "https://admin.atdesk.thesortedclub.com",
            "https://runner.atdesk.thesortedclub.com",
            "https://shop.atdesk.thesortedclub.com",
        ]
        if self.ALLOWED_ORIGINS:
            custom_origins = [orig.strip() for orig in self.ALLOWED_ORIGINS.split(",") if orig.strip()]
            for orig in custom_origins:
                if orig not in default_origins:
                    default_origins.append(orig)
        return default_origins

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    def validate_production_secrets(self):
        """
        Enforce fail-fast security constraints in production:
        Production MUST fail startup if required secrets are absent, predictable, or in mock mode.
        """
        if self.ENVIRONMENT.lower() in ["production", "prod"]:
            if not self.SECRET_KEY or self.SECRET_KEY == DEFAULT_DEV_SECRET:
                raise RuntimeError(
                    "FATAL SECURITY FAILURE: Production deployment detected with absent or default predictable SECRET_KEY! "
                    "You must provide a high-entropy SECRET_KEY (>= 32 characters) via environment variable."
                )
            if len(self.SECRET_KEY) < 32:
                raise RuntimeError("FATAL SECURITY FAILURE: Production SECRET_KEY must be at least 32 characters.")
            if not self.RAZORPAY_KEY_ID or self.RAZORPAY_KEY_ID.startswith("rzp_test_AtDeskDemo"):
                raise RuntimeError("FATAL SECURITY FAILURE: Production requires real Razorpay credentials (rzp_live_* or merchant approved rzp_test_*), not mock demo keys.")
            if not self.RAZORPAY_KEY_SECRET or self.RAZORPAY_KEY_SECRET == "rzp_test_secret_AtDeskSecurityKey":
                raise RuntimeError("FATAL SECURITY FAILURE: Production Razorpay RAZORPAY_KEY_SECRET must be configured.")
            if not self.RAZORPAY_WEBHOOK_SECRET or self.RAZORPAY_WEBHOOK_SECRET == "atdesk_razorpay_webhook_secret_key_2026":
                raise RuntimeError("FATAL SECURITY FAILURE: Production Razorpay RAZORPAY_WEBHOOK_SECRET must be set to a custom secret.")
            if self.SMS_PROVIDER not in ["GUPSHUP", "MSG91"]:
                raise RuntimeError("FATAL SECURITY FAILURE: Production SMS_PROVIDER must be 'GUPSHUP' or 'MSG91'. Mock SMS is forbidden in production.")
            if not self.SMS_API_KEY:
                raise RuntimeError("FATAL SECURITY FAILURE: Production SMS_API_KEY must be configured for DLT OTP delivery.")

settings = Settings()
