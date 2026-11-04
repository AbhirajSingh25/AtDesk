# AtDesk — Good things, delivered to your desk.
**A Product of The Sorted Club**  
*Initial Commercial Launch: JMD Megapolis, Sector 48, Gurugram, Haryana, India*

AtDesk is an enterprise multi-vendor food and essentials ordering and delivery platform built specifically for commercial tech parks and corporate campus towers, starting with **JMD Megapolis, Sector 48, Gurugram**.

Employees order from multiple nearby concourse shops in **one unified transaction**, pay AtDesk once with **one flat delivery fee (₹25)**, and AtDesk coordinates shop preparation, runner pickup, and **direct-to-desk delivery** via its own dedicated campus runner workforce.

---

## 1. Distinct Role Architectures

AtDesk delivers **four purpose-built user experiences** powered by a single high-performance FastAPI backend and PostgreSQL database:

| Role Experience | Distribution Channel | Target Audience | Primary Responsibilities |
| :--- | :--- | :--- | :--- |
| **Employee Customer App** | Android APK / PWA (`/`) | Office Employees at JMD Megapolis | Vendor discovery, multi-shop unified cart, desk picker (Towers A/B/C/D, Floors 1-14), Razorpay Checkout, live order tracking, 6-digit handover OTP. Strict customer view with **zero admin/runner access**. |
| **Campus Runner App** | Android APK / PWA (`/runner`, `/delivery`) | Dedicated Campus Delivery Partners | Phone SMS OTP login, shift toggle, multi-shop pickup checklist, real hardware camera proof, real device GPS coordinates, customer OTP verification. |
| **Shop Order Inbox** | Lightweight Web PWA (`/shop-inbox`) | Concourse Food & Retail Vendors | Incoming audio/visual order alerts, preparation time selector, status progression (Preparing -> Ready for Pickup), 86 / Out of Stock real-time toggle. |
| **Operations Admin Console** | Protected Web (`/admin`) | Operations Managers & Supervisors | Desktop sidebar & mobile bottom navigation, live exception queue (unaccepted, delayed, out of stock), database catalogue CRUD, bulk CSV menu upload, promo & coupon engine, daily settlements, supervisor OTP reveal with audit logging. |

---

## 2. Design Tokens & Visual Hierarchy

AtDesk features an earthy, modern, utilitarian palette crafted for workplace readability:

| Design Token | Hex Code | Visual Application |
| :--- | :--- | :--- |
| **Forest Green** | `#103D32` | Primary brand identity, top headers, primary actions |
| **Warm Ivory** | `#F7F4EC` | Application background, tactile paper texture feel |
| **Soft Sage** | `#DDE9D9` | Secondary surfaces, category pills, badges |
| **Tangerine** | `#E9A16D` | Accent callouts, countdown timers, status alerts |
| **Charcoal** | `#282B29` | High-contrast typography, structural borders |

---

## 3. Technology Stack

- **Backend:** FastAPI, Python 3.11, Pydantic V2, SQLAlchemy 2.0 (AsyncIO), Alembic.
- **Database:** PostgreSQL 18 with Row-Level Locking (`FOR UPDATE`) for atomic transactions.
- **Frontend:** Next.js 14 (App Router), React 18, TypeScript, Tailwind CSS, Lucide Icons.
- **Mobile Native:** Capacitor 8 with dual product flavors (`employee` and `runner`), Android Target SDK 35 (Android 15), Min SDK 24.
- **Payments:** Razorpay Standard Checkout SDK + server-side HMAC-SHA256 signature verification & idempotent webhooks.
- **Hardware Integration:** Hardware Camera API (Capacitor Camera), Geolocation API (Capacitor Geolocation).

---

## 4. Local Development Quickstart

### Prerequisites
- Python 3.11+
- Node.js 18+ and npm
- PostgreSQL 14+
- Android Studio / Android SDK (for mobile builds)

### 1. Database Setup
Ensure PostgreSQL is running on `127.0.0.1:5433` (or update `DATABASE_URL`):
```bash
createdb -p 5433 atdesk_staging
```

### 2. Backend Setup
```bash
# Set Python path
$env:PYTHONPATH = "."

# Install dependencies
pip install -r backend/requirements.txt

# Start FastAPI server
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```
API Documentation will be available at `http://localhost:8000/docs`.

### 3. Frontend Setup
```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```
Open `http://localhost:3000` in your browser.

---

## 5. Automated Verification & Testing

Run all 27 automated backend tests:
```powershell
$env:PYTHONPATH = "."
py -3.11 -m pytest backend/tests/ -v
```

Run end-to-end release check script:
```powershell
.\scripts\release-check.ps1
```

---

## 6. Android Mobile Build Commands

### Employee App (`com.thesortedclub.atdesk`):
```powershell
.\scripts\build-employee-android.ps1
```
- **Debug APK:** `frontend/android/app/build/outputs/apk/employee/debug/app-employee-debug.apk`
- **Release AAB:** `frontend/android/app/build/outputs/bundle/employeeRelease/app-employee-release.aab`

### Runner App (`com.thesortedclub.atdesk.runner`):
```powershell
.\scripts\build-runner-android.ps1
```
- **Debug APK:** `frontend/android/app/build/outputs/apk/runner/debug/app-runner-debug.apk`
- **Release AAB:** `frontend/android/app/build/outputs/bundle/runnerRelease/app-runner-release.aab`

---

## 7. Project Documentation Index

- [DEPLOYMENT.md](file:///c:/Users/user/Desktop/AtDesk/DEPLOYMENT.md) — Cloud deployment guide (Render, Neon, Vercel, Cloudflare R2).
- [PRODUCTION_ENVIRONMENT.md](file:///c:/Users/user/Desktop/AtDesk/PRODUCTION_ENVIRONMENT.md) — Production environment variables specification.
- [DATABASE_SETUP.md](file:///c:/Users/user/Desktop/AtDesk/DATABASE_SETUP.md) — Managed PostgreSQL provisioning, migrations & pooling.
- [SMS_OTP_SETUP.md](file:///c:/Users/user/Desktop/AtDesk/SMS_OTP_SETUP.md) — Indian DLT SMS OTP registration and provider integration.
- [RAZORPAY_SETUP.md](file:///c:/Users/user/Desktop/AtDesk/RAZORPAY_SETUP.md) — Razorpay payment gateway, webhooks, and test mode credentials.
- [FIREBASE_SETUP.md](file:///c:/Users/user/Desktop/AtDesk/FIREBASE_SETUP.md) — Firebase Cloud Messaging push notification setup.
- [ANDROID_RELEASE.md](file:///c:/Users/user/Desktop/AtDesk/ANDROID_RELEASE.md) — Keystore generation, APK signing, and Play Console release.
- [PLAY_STORE_CHECKLIST.md](file:///c:/Users/user/Desktop/AtDesk/PLAY_STORE_CHECKLIST.md) — Google Play Store submission requirements and data safety.
- [ADMIN_OPERATIONS_GUIDE.md](file:///c:/Users/user/Desktop/AtDesk/ADMIN_OPERATIONS_GUIDE.md) — Operations manual for JMD Megapolis campus console.
- [QA_REPORT.md](file:///c:/Users/user/Desktop/AtDesk/QA_REPORT.md) — Test logs and validation report.
- [RELEASE_BLOCKERS.md](file:///c:/Users/user/Desktop/AtDesk/RELEASE_BLOCKERS.md) — External credential checklist and action items.
