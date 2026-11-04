# AtDesk Production Deployment Guide

This document outlines the cloud deployment topology for AtDesk across managed infrastructure providers with tested, verified commands.

---

## 1. Cloud Architecture Overview

```
                        [ Cloudflare DNS / SSL ]
                                   │
         ┌─────────────────────────┴─────────────────────────┐
         │                                                   │
         ▼                                                   ▼
[ Vercel / Cloudflare Pages ]                        [ Render / AWS ECS ]
  Next.js 14 Responsive PWA                             FastAPI Async REST API
  • Employee Web (/)                                  • Auth & OTP Services
  • Runner Web (/runner)                              • Multi-Shop Orders
  • Shop Inbox (/shop-inbox)                          • Razorpay Webhooks
  • Operations Console (/admin)                       • Runner GPS Tracking
         │                                                   │
         │ (REST / JSON)                                     │ (AsyncPG / SSL)
         └─────────────────────────┬─────────────────────────┘
                                   │
                                   ▼
                    [ Neon Serverless / AWS RDS ]
                      PostgreSQL 18 Managed DB
                      • 34 Entities with Foreign Keys
                      • Strict Row-Level Locking (FOR UPDATE)
                                   │
                                   ▼
                       [ Cloudflare R2 / AWS S3 ]
                       Delivery Proof Storage (Private Pre-signed URLs)
```

---

## 2. Managed Database Provisioning & Migrations

### A. Neon Serverless PostgreSQL Setup
1. Sign in to [Neon Console](https://console.neon.tech).
2. Create project `atdesk-production` in region `ap-southeast-1` (Singapore) or `eu-central-1` (or AWS RDS `ap-south-1` Mumbai).
3. Copy the pooled connection string:
   ```
   postgresql+asyncpg://<user>:<password>@<endpoint>-pooler.neon.tech/atdesk?ssl=require
   ```

### B. Tested Migration Command for Render / CI Deployments
To run migrations from the repository root:
```bash
# Set production database connection string
export DATABASE_URL="postgresql+asyncpg://<user>:<password>@<endpoint>/atdesk?ssl=require"
export PYTHONPATH="."

# Execute versioned Alembic migration to HEAD (Creates all 34 tables)
alembic upgrade head
```
Or with explicit config file:
```bash
alembic -c backend/alembic.ini upgrade head
```

---

## 3. Backend Deployment: Render Web Service

1. Sign in to [Render Dashboard](https://dashboard.render.com).
2. Click **New +** -> **Web Service**.
3. Connect your repository: `https://github.com/AbhirajSingh25/AtDesk`.
4. Configure service settings:
   - **Name:** `atdesk-api`
   - **Region:** Singapore / Frankfurt
   - **Branch:** `rebuild/role-separation` (or `main`)
   - **Root Directory:** Leave blank
   - **Runtime:** `Python 3`
   - **Build Command:** `pip install -r backend/requirements.txt && alembic upgrade head`
   - **Start Command:** `uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT`
5. Set Environment Variables in Render:
   - `ENVIRONMENT`: `production`
   - `DATABASE_URL`: `postgresql+asyncpg://<user>:<password>@<host>/<database>?ssl=require`
   - `SECRET_KEY`: High-entropy string (>= 32 characters, generated via `python -c "import secrets; print(secrets.token_hex(32))"`)
   - `ALLOWED_ORIGINS`: `https://atdesk.thesortedclub.com,https://admin.atdesk.thesortedclub.com,https://runner.atdesk.thesortedclub.com,https://shop.atdesk.thesortedclub.com`
   - `RAZORPAY_KEY_ID`: `rzp_live_*`
   - `RAZORPAY_KEY_SECRET`: Your Razorpay Secret
   - `RAZORPAY_WEBHOOK_SECRET`: Your Webhook Secret
   - `SMS_PROVIDER`: `GUPSHUP` or `MSG91`
   - `SMS_API_KEY`: Your SMS provider API auth key
   - `SMS_SENDER_ID`: `SORTED`
   - `SMS_DLT_PE_ID`: Registered 19-digit Principal Entity ID
   - `SMS_DLT_TEMPLATE_ID`: Registered OTP template ID
   - `STORAGE_BACKEND`: `S3_PRIVATE` or `CLOUDFLARE_R2`
   - `S3_BUCKET_NAME`: `atdesk-delivery-proofs-private`
   - `AWS_ACCESS_KEY_ID`: S3/R2 Access Key
   - `AWS_SECRET_ACCESS_KEY`: S3/R2 Secret Key
   - `S3_ENDPOINT_URL`: Optional (for Cloudflare R2: `https://<account_id>.r2.cloudflarestorage.com`)

---

## 4. Frontend Deployment: Vercel

1. Sign in to [Vercel Dashboard](https://vercel.com).
2. Click **Add New...** -> **Project**.
3. Import `AbhirajSingh25/AtDesk`.
4. Configure Project:
   - **Framework Preset:** Next.js
   - **Root Directory:** `frontend`
   - **Build Command:** `next build`
   - **Output Directory:** `out`
5. Environment Variables:
   - `NEXT_PUBLIC_API_URL`: `https://api.atdesk.thesortedclub.com/api` (or your deployed Render URL `https://atdesk-api.onrender.com/api`).
   - `NEXT_PUBLIC_RAZORPAY_KEY_ID`: `rzp_live_*` (or test key)
6. Click **Deploy**.

---

## 5. Domain Configuration (Cloudflare DNS)

| Type | Name | Content | Proxy status |
| :--- | :--- | :--- | :--- |
| `CNAME` | `atdesk` | `cname.vercel-dns.com` | Proxied |
| `CNAME` | `admin.atdesk` | `cname.vercel-dns.com` | Proxied |
| `CNAME` | `runner.atdesk` | `cname.vercel-dns.com` | Proxied |
| `CNAME` | `shop.atdesk` | `cname.vercel-dns.com` | Proxied |
| `CNAME` | `api.atdesk` | `atdesk-api.onrender.com` | Proxied / DNS only |
