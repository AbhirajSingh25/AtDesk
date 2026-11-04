# AtDesk Production Deployment Guide

This document outlines the cloud deployment topology for AtDesk across managed infrastructure providers.

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
                      • 28+ Entities with Foreign Keys
                      • Strict Row-Level Locking (FOR UPDATE)
                                   │
                                   ▼
                       [ Cloudflare R2 / S3 ]
                       Delivery Proof Storage (Private)
```

---

## 2. Managed Database: Neon PostgreSQL

1. Sign in to [Neon Console](https://console.neon.tech).
2. Create project `atdesk-production` in region `ap-southeast-1` (Singapore) or `eu-central-1` (or AWS RDS `ap-south-1` Mumbai).
3. Copy the pooled connection string:
   ```
   postgresql+asyncpg://<user>:<password>@<endpoint>-pooler.neon.tech/atdesk?ssl=require
   ```
4. Run Alembic migrations against the production database:
   ```bash
   DATABASE_URL="postgresql+asyncpg://..." alembic upgrade head
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
   - **Root Directory:** Leave blank (or `backend`)
   - **Runtime:** `Python 3`
   - **Build Command:** `pip install -r backend/requirements.txt`
   - **Start Command:** `uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT`
5. Set Environment Variables in Render:
   - `DATABASE_URL`: Your Neon/RDS asyncpg connection string.
   - `SECRET_KEY`: Generate via `python -c "import secrets; print(secrets.token_hex(32))"`.
   - `ALLOWED_ORIGINS`: `https://atdesk.thesortedclub.com,https://admin.atdesk.thesortedclub.com`.
   - `RAZORPAY_KEY_ID`: `rzp_live_*`
   - `RAZORPAY_KEY_SECRET`: Your Razorpay Secret.
   - `DLT_OTP_TEMPLATE_ID`: Your DLT registered template ID.
   - `SMS_GATEWAY_API_KEY`: Gupshup/MSG91 API Key.

---

## 4. Frontend Deployment: Vercel

1. Sign in to [Vercel Dashboard](https://vercel.com).
2. Click **Add New...** -> **Project**.
3. Import `AbhirajSingh25/AtDesk`.
4. Configure Project:
   - **Framework Preset:** Next.js
   - **Root Directory:** `frontend`
   - **Build Command:** `next build`
   - **Output Directory:** `out` (or default Next.js output)
5. Environment Variables:
   - `NEXT_PUBLIC_API_URL`: `https://atdesk-api.onrender.com` (your deployed FastAPI backend URL).
6. Click **Deploy**.

---

## 5. Domain Configuration (Cloudflare DNS)

| Type | Name | Content | Proxy status |
| :--- | :--- | :--- | :--- |
| `CNAME` | `atdesk` | `cname.vercel-dns.com` | Proxied |
| `CNAME` | `admin.atdesk` | `cname.vercel-dns.com` | Proxied |
| `CNAME` | `api.atdesk` | `atdesk-api.onrender.com` | Proxied (or DNS only) |
