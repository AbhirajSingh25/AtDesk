# AtDesk Codebase Audit & Gap Analysis

**Campus Pilot:** JMD Megapolis, Sector 48, Gurugram  
**Parent Brand:** The Sorted Club  
**Stack:** FastAPI (Python 3.11), PostgreSQL 18 (Port 5433), Next.js 14, Tailwind CSS, Capacitor Android  

---

## 1. Executive Summary & Baseline Findings

A forensic audit of the existing AtDesk repository was conducted. While core database schemas, PostgreSQL async engine bindings, and financial models exist, significant architectural coupling, security bypasses, UI hardcoding, and simulated behaviors require systematic reconstruction.

### Baseline Status Matrix
| Subsystem | Current State | Target State | Priority |
| :--- | :--- | :--- | :--- |
| **Authentication & RBAC** | Optional auth on critical endpoints, fixed `user_id=1` and `partner_id=1` defaults | Mandatory JWT Bearer auth, strict role gating (`EMPLOYEE`, `DELIVERY_PARTNER`, `ADMIN`, `SHOP_STAFF`) | **P0 (Critical)** |
| **Secret Management** | Predictable hardcoded default `SECRET_KEY` in `config.py` | Strict environment-driven secrets; fail fast on missing secrets in production | **P0 (Critical)** |
| **Payments** | `PaymentModal.tsx` simulates gateway via `setTimeout(1200ms)`; bypasses Razorpay signature verification | Real Razorpay Checkout flow: server order creation, signature verification, idempotent webhook processing | **P0 (Critical)** |
| **Role Separation** | Single global `RoleSwitcher` in `layout.tsx` linking Employee, Delivery, and Admin together | 4 distinct decoupled role experiences; dedicated Android packages for Employee and Runner; zero cross-navigation | **P0 (Critical)** |
| **Delivery Evidence** | Fabricated base64 strings and hardcoded GPS coordinates (28.4162, 77.0425) on camera/GPS denial | Strict hardware camera and browser GPS enforcement; submission blocked if permissions denied; no synthetic evidence | **P1 (High)** |
| **Shop Operations** | No dedicated shop staff interface; shops cannot accept/reject orders or toggle availability live | Lightweight responsive Web/PWA Shop Order Inbox for line cooks/staff to accept, prep, mark ready, or 86 items | **P1 (High)** |
| **Operations Automation** | Orders require manual admin advancement; no event-driven lifecycle or automatic runner dispatch | Automated lifecycle: Payment -> Shop notify -> Accept/Reject -> Dynamic ETA -> Runner auto-dispatch -> OTP/Proof -> Ledger | **P1 (High)** |
| **Catalogue Management** | Product catalog hardcoded in `AdminDashboard.tsx` array (lines 586-595); no CSV import or coupon management | Database-backed CRUD for shops/categories/items, bulk CSV menu upload, live availability toggle, coupon engine | **P1 (High)** |
| **Admin Operations** | Customer 6-digit master OTPs exposed in plain text in tables; hardcoded KPI percentages (96.4%, 78.2%) | Masked OTP with privileged audit reveal; computed live database KPIs; desktop + mobile bottom-nav ops console | **P1 (High)** |
| **Mobile Delivery Packages** | Single Android build configuration pointing to localhost | Dual Android configurations: `com.thesortedclub.atdesk` (Customer) and `com.thesortedclub.atdesk.runner` (Runner) | **P1 (High)** |

---

## 2. Forensic Gap List by Domain

### A. Security & Authorization Gaps
1. **Unprotected Endpoints**: `backend/app/api/orders.py`, `backend/app/api/delivery.py`, and `backend/app/api/admin.py` frequently employ `get_current_user_optional`. If no Bearer token is provided, endpoints default to `user_id = 1` or `partner_id = 1`.
2. **Predictable Fallbacks**: `SECRET_KEY` in `backend/app/core/config.py` defaults to `"atdesk-the-sorted-club-secure-token-2026-jmd-megapolis"`. If deployed without explicit environment variables, tokens can be forged.
3. **CORS Permissiveness**: `CORS_ORIGINS` currently contains only localhost references. Needs structured support for approved staging, production domains, and Capacitor origins (`capacitor://localhost`, `http://localhost`).
4. **OTP Exposure**: `master_otp` is returned indiscriminately in order serializer outputs and visible to admin tables without auditing.

### B. Payment & Checkout Gaps
1. **Frontend Simulation**: `PaymentModal.tsx` contains `await new Promise((r) => setTimeout(r, 1200))` and calls `submitOrder("UPI")` without interacting with Razorpay's JavaScript SDK or standard checkout handler.
2. **Order Creation Disconnect**: Backend possesses Razorpay order creation endpoints (`/api/payments/razorpay/create-order`), but customer checkout never initiates this flow.
3. **Webhook Verification**: Webhook handler requires strict idempotent replay prevention and signature verification before marking orders `PAID`.

### C. Application Decoupling Gaps
1. **Global RoleSwitcher**: Placed in `frontend/src/app/layout.tsx`. Any employee using the PWA or APK can see pills for "Delivery Partner" and "Admin Center".
2. **Missing Vendor Inbox**: Shopkeepers have no portal. When an order is placed, vendor order status remains `PENDING` unless an admin manually clicks "Advance" in the dashboard.
3. **Runner Experience**: The delivery page is coupled into the same Next.js router (`/delivery`), lacking dedicated runner authentication, shift online/offline toggling, and shop collection checklists.

### D. Operations & Automation Gaps
1. **Manual Order Advancement**: Admin is expected to click "Advance" through `OUT_FOR_DELIVERY` and `DELIVERED`, which does not scale beyond 5 orders.
2. **Missing Acceptance Timeout**: No automated escalation if a vendor does not accept an order within 3 minutes.
3. **Out of Stock Protocol**: If a vendor runs out of an ingredient, there is no in-app mechanism for the vendor to reject a child item and trigger immediate partial refund calculations.
4. **Evidence Fabrication**: `DeliveryApp.tsx` lines 97-100 fall back to `"data:image/jpeg;base64,/9j/4AAQSkZJRgABAQEASABIAAD_DESK_PROOF_EVIDENCE..."` when camera access is denied, and fallback coordinates `28.4162, 77.0425` when GPS is unavailable.

### E. Catalogue & Promotion Gaps
1. **Hardcoded Menu Items in Admin**: `AdminDashboard.tsx` contains static mock items for price updates instead of querying `/api/admin/menu-items` or `/api/shops/{id}`.
2. **Lack of Coupon Engine**: No data model or endpoints for discount codes (e.g., flat ₹50 off, percentage discounts, minimum order constraints).
3. **Bulk CSV Import**: No bulk import endpoint for vendors or admins uploading large menus.

---

## 3. Implementation Plan & Discipline

The rebuild will be executed in sequential, committed phases:

- **Phase 1**: Forensic Audit, baseline tests, and gap cataloging.
- **Phase 2**: Backend security hardening: require authentication on protected endpoints, role authorization, dynamic startup check for production secrets, coupon/promotion models, shop staff user role, Razorpay checkout integration with idempotent webhook.
- **Phase 3**: Operations automation engine: shop order inbox endpoints, auto-assignment of runners, rejection and cancellation refund automation, order notification delivery.
- **Phase 4**: Customer App overhaul: Swiggy-style visual hierarchy, JMD Megapolis desk picker, category shortcuts, featured shops, cart drawer, real Razorpay Checkout modal, live status tracking without RoleSwitcher.
- **Phase 5**: Runner App overhaul: Runner authentication, live job assignment, shop pickup checklist, strict camera-only proof (blocking on denial), GPS location verification, customer OTP verification.
- **Phase 6**: Shop Order Inbox & Operations Admin: Lightweight responsive vendor inbox web app; Admin operations console with mobile bottom navigation, catalogue CRUD, bulk CSV upload, promo manager, exception queue, masked OTP with supervisor reveal.
- **Phase 7**: Dual Android APK packaging (`com.thesortedclub.atdesk` and `com.thesortedclub.atdesk.runner`), comprehensive test suite execution, frontend build & typecheck.

