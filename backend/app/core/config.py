import os
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "AtDesk"
    VERSION: str = "2.0.0-staging"
    TAGLINE: str = "Good things, delivered to your desk."
    PARENT_BRAND: str = "The Sorted Club"
    LAUNCH_LOCATION: str = "JMD Megapolis, Sector 48, Gurugram, Haryana, India"
    
    # 1. Managed PostgreSQL Staging Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        "postgresql+asyncpg://postgres:atdesk_staging@127.0.0.1:5433/atdesk_staging"
    )
    
    # 2. Security & JWT
    SECRET_KEY: str = os.getenv("SECRET_KEY", "atdesk-the-sorted-club-secure-token-2026-jmd-megapolis")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    
    # 3. Operational Policies
    FLAT_DELIVERY_FEE: float = 25.00  # Exactly one flat delivery fee across all shops
    CANCELLATION_WINDOW_SECONDS: int = 120  # Strict 2-minute server-authoritative window
    MIN_SHOP_PREPAID_ALERT_THRESHOLD: float = 1500.00
    
    # 4. Indian DLT SMS Configuration
    SMS_PROVIDER: str = os.getenv("SMS_PROVIDER", "GUPSHUP")  # GUPSHUP | EXOTEL | STAGING_ADAPTER
    SMS_API_KEY: str = os.getenv("SMS_API_KEY", "test_sms_api_key_atdesk")
    SMS_SENDER_ID: str = os.getenv("SMS_SENDER_ID", "SORTED")
    SMS_DLT_PE_ID: str = os.getenv("SMS_DLT_PE_ID", "1701159876543210987")  # Principal Entity ID
    SMS_DLT_TEMPLATE_ID: str = os.getenv("SMS_DLT_TEMPLATE_ID", "1707161234567890123")  # DLT Registered Template
    OTP_VALIDITY_SECONDS: int = 300  # 5 minutes
    OTP_RESEND_COOLDOWN_SECONDS: int = 60  # Minimum 60s cooldown
    OTP_MAX_ATTEMPTS: int = 3  # Max 3 attempts before lockout
    
    # 5. Razorpay Gateway (Test Mode Credentials)
    RAZORPAY_KEY_ID: str = os.getenv("RAZORPAY_KEY_ID", "rzp_test_AtDeskDemo2026")
    RAZORPAY_KEY_SECRET: str = os.getenv("RAZORPAY_KEY_SECRET", "rzp_test_secret_AtDeskSecurityKey")
    RAZORPAY_WEBHOOK_SECRET: str = os.getenv("RAZORPAY_WEBHOOK_SECRET", "atdesk_razorpay_webhook_secret_key_2026")
    
    # 6. Private Cloud Storage (AWS S3 / Cloud Storage for Delivery Evidence)
    STORAGE_BACKEND: str = os.getenv("STORAGE_BACKEND", "S3_PRIVATE")  # S3_PRIVATE | LOCAL_ENCRYPTED
    S3_BUCKET_NAME: str = os.getenv("S3_BUCKET_NAME", "atdesk-delivery-proofs-jmd-private")
    AWS_REGION: str = os.getenv("AWS_REGION", "ap-south-1")  # Mumbai Region
    AWS_ACCESS_KEY_ID: str = os.getenv("AWS_ACCESS_KEY_ID", "mock_aws_access_key_atdesk")
    AWS_SECRET_ACCESS_KEY: str = os.getenv("AWS_SECRET_ACCESS_KEY", "mock_aws_secret_key_atdesk")
    S3_PRESIGNED_EXPIRATION_SECONDS: int = 900  # 15 minutes max lifetime for pre-signed URLs
    MAX_UPLOAD_SIZE_BYTES: int = 5 * 1024 * 1024  # 5 MB max
    
    # 7. Google Maps Platform & GPS Engine
    GOOGLE_MAPS_SERVER_API_KEY: str = os.getenv("GOOGLE_MAPS_SERVER_API_KEY", "AIzaSy_MockGoogleMapsServerKey_AtDesk_JMD")
    JMD_MEGAPOLIS_LATITUDE: float = 28.4162
    JMD_MEGAPOLIS_LONGITUDE: float = 77.0425
    
    # 8. Firebase Cloud Messaging (FCM)
    FCM_SERVER_KEY: str = os.getenv("FCM_SERVER_KEY", "mock_fcm_server_key_thesortedclub")
    FCM_PROJECT_ID: str = os.getenv("FCM_PROJECT_ID", "atdesk-notifications-pilot")
    
    # 9. JMD Megapolis Configuration
    JMD_TOWERS: List[str] = ["Tower A", "Tower B", "Tower C", "Tower D"]
    JMD_FLOORS: List[int] = list(range(1, 15))
    
    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ]

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
