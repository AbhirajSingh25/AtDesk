# AtDesk Production Environment Variables (Canonical Reference)

This document defines all environment variables required by the AtDesk platform in production. Every variable listed here is actively consumed by the running backend or frontend.

> [!IMPORTANT]
> Never commit actual passwords, private keys, or API tokens to source control. Configure these variables directly inside your hosting platform's secure environment manager (Render, Vercel, AWS Secrets Manager, GitHub Secrets).

---

## 1. Backend Environment Variables (FastAPI)

| Variable Name | Required in Prod | Default / Format | Description | Consumed In |
| :--- | :--- | :--- | :--- | :--- |
| `ENVIRONMENT` | **Yes** | `production` | Deployment mode: `development`, `staging`, `production`. When `production`, security guardrails fail startup if dummy keys are present. | `config.py` |
| `DATABASE_URL` | **Yes** | `postgresql+asyncpg://<user>:<pass>@<host>:5432/<db>?ssl=require` | Managed PostgreSQL connection string using the asyncpg driver. | `config.py`, `database.py`, `alembic/env.py` |
| `SECRET_KEY` | **Yes** | 64-char hex string | Cryptographic secret for signing JWT auth tokens. Must be >= 32 characters. Fails startup if missing or default. | `config.py`, `security.py`, `storage_service.py` |
| `ALGORITHM` | No | `HS256` | JWT signing algorithm. | `config.py`, `security.py` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | `43200` (30 days) | JWT lifetime before expiration. | `config.py`, `security.py` |
| `ALLOWED_ORIGINS` | **Yes** | Comma-separated URLs | Approved CORS origins (e.g. `https://atdesk.thesortedclub.com,https://admin.atdesk.thesortedclub.com`). | `config.py`, `main.py` |
| `RAZORPAY_KEY_ID` | **Yes** | `rzp_live_*` or `rzp_test_*` | Razorpay Merchant Key ID. Fails startup if default demo key in production. | `config.py`, `payment_gateway.py` |
| `RAZORPAY_KEY_SECRET` | **Yes** | String | Razorpay Merchant Secret for client payment HMAC signature verification. | `config.py`, `payment_gateway.py` |
| `RAZORPAY_WEBHOOK_SECRET` | **Yes** | String | Secret configured in Razorpay Webhooks dashboard for mandatory HMAC SHA-256 webhook validation. | `config.py`, `payments.py`, `payment_gateway.py` |
| `SMS_PROVIDER` | **Yes** | `GUPSHUP` or `MSG91` | DLT SMS gateway provider. `TEST_MOCK` is strictly forbidden in production. | `config.py`, `sms_service.py` |
| `SMS_API_KEY` | **Yes** | String | API auth key for DLT transactional SMS dispatch. | `config.py`, `sms_service.py` |
| `SMS_SENDER_ID` | **Yes** | `SORTED` | 6-character registered TRAI DLT sender header. | `config.py`, `sms_service.py` |
| `SMS_DLT_PE_ID` | **Yes** | `1701XXXXXXXXXXXXXXXX` | 19-digit TRAI DLT Principal Entity ID. | `config.py`, `sms_service.py` |
| `SMS_DLT_TEMPLATE_ID` | **Yes** | `1707XXXXXXXXXXXXXXXX` | Registered TRAI DLT OTP content template ID. | `config.py`, `sms_service.py` |
| `SMS_GUPSHUP_USERID` | No | String | Gupshup Enterprise Account User ID (if using user credentials). | `config.py`, `sms_service.py` |
| `SMS_GUPSHUP_PASSWORD` | No | String | Gupshup Enterprise Account Password (if using user credentials). | `config.py`, `sms_service.py` |
| `STORAGE_BACKEND` | No | `S3_PRIVATE` or `CLOUDFLARE_R2` | Private object storage backend for delivery photo proofs. | `config.py`, `storage_service.py` |
| `S3_BUCKET_NAME` | No | `atdesk-delivery-proofs-private` | Private bucket name for delivery photos. | `config.py`, `storage_service.py` |
| `S3_ENDPOINT_URL` | No | `https://<account_id>.r2.cloudflarestorage.com` | Storage endpoint URL (required for Cloudflare R2). | `config.py`, `storage_service.py` |
| `AWS_REGION` | No | `ap-south-1` | S3 region (Mumbai). Default: `ap-south-1` (or `auto` for R2). | `config.py`, `storage_service.py` |
| `AWS_ACCESS_KEY_ID` | No | String | S3 or R2 Access Key ID. Also accepts `S3_ACCESS_KEY`. | `config.py`, `storage_service.py` |
| `AWS_SECRET_ACCESS_KEY` | No | String | S3 or R2 Secret Access Key. Also accepts `S3_SECRET_KEY`. | `config.py`, `storage_service.py` |
| `FCM_SERVER_KEY` | No | String | Firebase Cloud Messaging server key for push notifications. | `config.py`, `notification_service.py` |
| `FCM_PROJECT_ID` | No | `atdesk-notifications-pilot` | Firebase project identifier. | `config.py`, `notification_service.py` |

---

## 2. Frontend Environment Variables (Next.js & Capacitor)

| Variable Name | Required | Example Value | Description |
| :--- | :--- | :--- | :--- |
| `NEXT_PUBLIC_API_URL` | **Yes** | `https://api.atdesk.thesortedclub.com/api` | Base URL of deployed FastAPI backend. Injected at build time into Next.js and Capacitor assets. Normalized automatically so trailing slashes and missing `/api` suffixes are corrected. In production, never falls back to localhost. |
| `NEXT_PUBLIC_RAZORPAY_KEY_ID` | **Yes** | `rzp_live_*` or `rzp_test_*` | Public Razorpay key ID passed to Razorpay Checkout JavaScript SDK. |
