#!/usr/bin/env python3
"""
AtDesk Production Configuration Validator
Validates environment variables and critical service configurations without exposing sensitive values.
"""
import os
import sys

CRITICAL_ENV_VARS = [
    ("DATABASE_URL", True, "PostgreSQL connection string (e.g. Neon, AWS RDS)"),
    ("SECRET_KEY", True, "FastAPI cryptographic secret key (>= 32 chars)"),
    ("ALGORITHM", False, "JWT signing algorithm (default: HS256)"),
    ("ACCESS_TOKEN_EXPIRE_MINUTES", False, "JWT expiry in minutes"),
    ("RAZORPAY_KEY_ID", True, "Razorpay API key id (rzp_live_* or rzp_test_*)"),
    ("RAZORPAY_KEY_SECRET", True, "Razorpay webhook/API secret"),
    ("SMS_GATEWAY_PROVIDER", False, "DLT SMS Provider: GUPSHUP or MSG91"),
    ("SMS_GATEWAY_API_KEY", True, "DLT SMS API key"),
    ("DLT_OTP_TEMPLATE_ID", True, "DLT registered SMS OTP template ID"),
    ("DLT_SENDER_ID", True, "DLT registered 6-character sender ID"),
    ("FIREBASE_CREDENTIALS_JSON", False, "Firebase Cloud Messaging service account credentials path or json"),
    ("STORAGE_BACKEND", False, "S3 or CLOUDFLARE_R2 for delivery proof photos"),
]

def check_env():
    print("=" * 60)
    print("AtDesk - Production Configuration Audit")
    print("=" * 60)
    
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
            if val in ("your_secret_key_here", "dummy", "placeholder", "changeme", "default"):
                missing_required.append((var_name, f"Value is an insecure placeholder: '{val}'"))
                print(f" [INSECURE PLACEHOLDER] {var_name:<26} -> Insecure default detected!")
            else:
                masked = val[:4] + "..." + val[-4:] if len(val) > 8 else "***"
                print(f" [OK]                  {var_name:<26} -> Configured ({masked})")

    print("\nSummary:")
    print(f"  Total variables checked: {len(CRITICAL_ENV_VARS)}")
    print(f"  Missing required:        {len(missing_required)}")
    print(f"  Optional unset:          {len(warnings)}")
    print("=" * 60)

    if missing_required:
        print("\nACTION REQUIRED: Set the missing required variables in your production environment before deploying.")
        return 1
    else:
        print("\nAll required production environment variables are present and configured!")
        return 0

if __name__ == "__main__":
    sys.exit(check_env())
