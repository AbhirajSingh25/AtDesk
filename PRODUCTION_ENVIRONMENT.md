# AtDesk Production Environment Variables

This document defines all environment variables required by the AtDesk platform in production.

> [!IMPORTANT]
> Never commit actual passwords, private keys, or API tokens to source control. Configure these variables directly inside your hosting platform's secure environment manager (Render, Vercel, AWS Secrets Manager, GitHub Secrets).

---

## 1. Backend Environment Variables (FastAPI)

| Variable Name | Required | Default / Format | Description |
| :--- | :--- | :--- | :--- |
| `DATABASE_URL` | **Yes** | `postgresql+asyncpg://user:pass@host:5432/dbname?ssl=require` | Connection string for PostgreSQL database with AsyncPG driver. |
| `SECRET_KEY` | **Yes** | `64-character hex string` | Cryptographic secret for signing JWT auth tokens. Must be >= 32 characters. Fails startup if default or missing. |
| `ALGORITHM` | No | `HS256` | JWT signing algorithm. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | `43200` (30 days) | JWT lifetime before refresh required. |
| `ALLOWED_ORIGINS` | **Yes** | `https://atdesk.thesortedclub.com,https://admin.atdesk.thesortedclub.com` | Comma-separated list of allowed CORS origins. |
| `ENVIRONMENT` | No | `production` | Deployment mode: `development`, `staging`, `production`. |
| `RAZORPAY_KEY_ID` | **Yes** | `rzp_live_*` or `rzp_test_*` | Razorpay Merchant Key ID. |
| `RAZORPAY_KEY_SECRET` | **Yes** | String | Razorpay Merchant Key Secret used for server-side order generation and signature verification. |
| `RAZORPAY_WEBHOOK_SECRET` | No | String | Secret configured in Razorpay Webhooks dashboard for HMAC validation. |
| `SMS_GATEWAY_PROVIDER` | No | `GUPSHUP` (or `MSG91`) | DLT SMS gateway provider. |
| `SMS_GATEWAY_API_KEY` | **Yes** | String | API key for sending DLT registered transactional SMS OTPs. |
| `DLT_OTP_TEMPLATE_ID` | **Yes** | String | Telecom Regulatory Authority of India (TRAI) DLT registered OTP template ID. |
| `DLT_SENDER_ID` | **Yes** | String | Registered 6-character alphabetic sender header (e.g. `SORTED`). |
| `FIREBASE_CREDENTIALS_JSON` | No | File path or JSON string | Google Firebase service account JSON for FCM push notifications to runners and employees. |
| `STORAGE_BACKEND` | No | `CLOUDFLARE_R2` or `S3` | S3-compatible object storage provider for runner delivery camera proof photos. |
| `S3_BUCKET_NAME` | No | `atdesk-delivery-proofs` | S3/R2 bucket name. |
| `S3_ACCESS_KEY` | No | String | Storage access key ID. |
| `S3_SECRET_KEY` | No | String | Storage secret access key. |
| `S3_ENDPOINT_URL` | No | `https://<account-id>.r2.cloudflarestorage.com` | Storage endpoint (for Cloudflare R2). |

---

## 2. Frontend Environment Variables (Next.js & Capacitor)

| Variable Name | Required | Default / Format | Description |
| :--- | :--- | :--- | :--- |
| `NEXT_PUBLIC_API_URL` | **Yes** | `https://api.atdesk.thesortedclub.com` | Base URL of deployed FastAPI backend. Injected at build time into Next.js and Capacitor native web assets. |
| `NEXT_PUBLIC_RAZORPAY_KEY_ID` | **Yes** | `rzp_live_*` or `rzp_test_*` | Public Razorpay key ID passed to Razorpay Checkout JavaScript SDK. |
| `NEXT_PUBLIC_CAMPUS_NAME` | No | `JMD Megapolis` | Default campus name. |
| `NEXT_PUBLIC_CAMPUS_CITY` | No | `Gurugram, Haryana` | Campus location. |
