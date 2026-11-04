#!/usr/bin/env python3
"""
AtDesk Production Configuration Validator
Validates environment variables and critical service configurations without exposing sensitive values.
"""
import os
import sys

CRITICAL_ENV_VARS = [
    ("DATABASE_URL", True, "PostgreSQL connection string (e.g. Neon, AWS RDS, Render)"),
    ("SECRET_KEY", True, "FastAPI cryptographic secret key (>= 32 chars, high entropy)"),
    ("ALLOWED_ORIGINS", True, "Comma-separated approved frontend origins for CORS"),
    ("RAZORPAY_KEY_ID", True, "Razorpay API key id (rzp_live_* or merchant approved rzp_test_*)"),
    ("RAZORPAY_KEY_SECRET", True, "Razorpay API secret"),
    ("RAZORPAY_WEBHOOK_SECRET", True, "Razorpay webhook HMAC SHA-256 secret"),
    ("SMS_PROVIDER", True, "DLT SMS Provider: GUPSHUP or MSG91 (TEST_MOCK forbidden in prod)"),
    ("SMS_API_KEY", True, "DLT SMS provider API auth key"),
    ("SMS_SENDER_ID", True, "DLT registered 6-character sender header (e.g. SORTED)"),
    ("SMS_DLT_PE_ID", True, "DLT Principal Entity ID (19 digits)"),
    ("SMS_DLT_TEMPLATE_ID", True, "DLT registered OTP content template ID"),
    ("STORAGE_BACKEND", False, "S3_PRIVATE or CLOUDFLARE_R2 for delivery proof photos"),
    ("S3_BUCKET_NAME", False, "S3/R2 private bucket name"),
    ("AWS_ACCESS_KEY_ID", False, "S3/R2 access key id"),
    ("AWS_SECRET_ACCESS_KEY", False, "S3/R2 secret access key"),
    ("FCM_SERVER_KEY", False, "Firebase Cloud Messaging server key"),
]

def check_env():
    print("=" * 65)
    print("AtDesk - Production Configuration Audit (Canonical)")
    print("=" * 65)
    
    missing_required = []
    warnings = []
    
    for var_name, required, description in CRITICAL_ENV_VARS:
        val = os.getenv(var_name)
        if not val:
            if required:
                missing_required.append((var_name, description))
                print(f" [MISSING - REQUIRED] {var_name:<26} -> {description}")
            else:
                warnings.append((var_name, description))
                print(f" [OPTIONAL - UNSET]    {var_name:<26} -> {description}")
        else:
            # Check for dummy/default values
            val_lower = val.lower().strip()
            if any(p in val_lower for p in ["dummy", "placeholder", "changeme", "default_secret", "insecure"]):
                missing_required.append((var_name, f"Value is an insecure placeholder: '{val}'"))
                print(f" [INSECURE PLACEHOLDER] {var_name:<26} -> Insecure default detected!")
            elif var_name == "SMS_PROVIDER" and val_lower in ["test_mock", "mock"]:
                missing_required.append((var_name, "Mock SMS provider cannot be used in production"))
                print(f" [FORBIDDEN IN PROD]   {var_name:<26} -> Mock SMS forbidden in production!")
            elif var_name == "SECRET_KEY" and len(val) < 32:
                missing_required.append((var_name, "SECRET_KEY must be at least 32 characters"))
                print(f" [INSUFFICIENT LENGTH] {var_name:<26} -> Must be >= 32 characters!")
            else:
                masked = val[:4] + "..." + val[-4:] if len(val) > 8 else "***"
                print(f" [CONFIGURED]          {var_name:<26} -> Valid format ({masked})")

    print("\nSummary:")
    print(f"  Total variables checked: {len(CRITICAL_ENV_VARS)}")
    print(f"  Missing required:        {len(missing_required)}")
    print(f"  Optional unset:          {len(warnings)}")
    print("=" * 65)

    if missing_required:
        print("\nACTION REQUIRED: Set the missing required variables in your production environment before deploying.")
        return 1
    else:
        print("\nAll required production environment variables are present and configured!")
        return 0

if __name__ == "__main__":
    sys.exit(check_env())
