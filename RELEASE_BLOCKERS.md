# AtDesk External Production Release Blockers

This document highlights the specific external accounts, credentials, KYC approvals, and domain verifications that require manual action by The Sorted Club's founders/administrators before live launch.

---

## 1. External Credential & Setup Checklist

| Service / Provider | Exact Required Information | Configuration Target | Action Required by User | Link / Portal |
| :--- | :--- | :--- | :--- | :--- |
| **Razorpay** | Live Key ID (`rzp_live_*`) & Key Secret | `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET` | Complete Business KYC for The Sorted Club, activate live mode, and copy API keys. | [Razorpay Dashboard](https://dashboard.razorpay.com/#/access/api-keys) |
| **Razorpay Webhooks** | Webhook Secret | `RAZORPAY_WEBHOOK_SECRET` | Add webhook endpoint `https://api.atdesk.thesortedclub.com/api/payments/razorpay/webhook` with events `order.paid`, `payment.captured`. | [Razorpay Webhooks](https://dashboard.razorpay.com/#/access/webhooks) |
| **TRAI / Telecom DLT** | Principal Entity ID, Sender Header (`SORTED`), OTP Template ID | `SMS_DLT_PE_ID`, `SMS_SENDER_ID`, `SMS_DLT_TEMPLATE_ID` | Register business entity on telecom DLT portal (Jio/Airtel/VI), register sender header, and register OTP content template. | [Jio DLT](https://trueconnect.jio.com) / [Airtel DLT](https://www.airtel.in/business/commercial-communication) |
| **Gupshup / MSG91** | Provider Choice & API Auth Key | `SMS_PROVIDER` (`GUPSHUP` or `MSG91`), `SMS_API_KEY` | Link DLT PE ID and Sender ID to Gupshup/MSG91 account and copy API auth key. | [Gupshup Dashboard](https://enterprise.smsgupshup.com) / [MSG91](https://msg91.com) |
| **Neon / AWS RDS** | Managed PostgreSQL connection string | `DATABASE_URL` | Provision production PostgreSQL instance and set connection string in Render. | [Neon Console](https://console.neon.tech) / [AWS RDS](https://console.aws.amazon.com/rds) |
| **Google Play Console** | Play Console Developer Account & Signing Keystore | Google Play Store Release | Pay one-time \$25 Google developer registration, generate keystore via `keytool`, and create app listings for both package IDs. | [Google Play Console](https://play.google.com/console) |
| **Firebase** | `google-services.json` | `frontend/android/app/src/employee/` and `src/runner/` | Create Firebase project, add both Android packages (`com.thesortedclub.atdesk` and `com.thesortedclub.atdesk.runner`), and download config. | [Firebase Console](https://console.firebase.google.com) |
| **DNS / Domain** | Domain DNS records | Cloudflare DNS | Add CNAME records for `atdesk.thesortedclub.com` and `api.atdesk.thesortedclub.com`. | Cloudflare / Domain Registrar |

---

## 2. Status of Code & Build Readiness

Everything that can be implemented in code and built locally has been completed and verified:
- Core role separation into 4 distinct experiences.
- Versioned Alembic migrations (`8683b34160e6`) creating all 34 database entities from scratch.
- Real provider HTTP integrations for Gupshup and MSG91 with DLT validation.
- Mandatory HMAC SHA-256 Razorpay webhook signature validation at `/api/payments/razorpay/webhook`.
- Normalized API URL resolution in Next.js preventing production fallback to localhost.
- Dual flavor Android debug APKs and release AABs compiled for both Employee and Runner.
- Automated release verification gate passing 100%.
