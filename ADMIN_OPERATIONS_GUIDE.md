# Operations Admin Manual: JMD Megapolis Campus

This operations manual guides hub managers and campus supervisors operating the AtDesk Command Center at JMD Megapolis, Sector 48, Gurugram.

---

## 1. Access & Role Authorization

- **URL:** `https://admin.atdesk.thesortedclub.com` (or `/admin` during local testing).
- **Required Role:** `ADMIN` or `SUPERVISOR`.
- **Security:** Protected by strict JWT authentication. Non-authenticated users or employees attempting to access `/admin` receive HTTP 403 Forbidden.

---

## 2. Real-Time Operations Features

### A. Live Exception Inbox
The system surfaces operations exceptions requiring human intervention:
1. **Unaccepted Orders:** Orders where a shop has not accepted within 3 minutes of customer payment.
   - *Quick Action:* Call shop staff directly or reassign to backup vendor.
2. **Preparation Delays:** Orders where elapsed preparation time exceeds the shop's committed duration.
   - *Quick Action:* Trigger status check or notify assigned runner.
3. **Out-of-Stock Alerts:** Orders where a shop rejected an item.
   - *Quick Action:* Trigger automatic partial refund or notify customer.

### B. Runner Availability & Dispatch
- View active campus runners, online/offline shift status, and current order workload.
- Automated dispatcher assigns orders to the runner with the lowest active load within the campus zone.
- Manual reassignment override available for runner emergencies or shift breaks.

### C. Catalogue & Menu Management (Zero Hardcoded Products)
- **Live Shops:** Create, edit name, contact phone, building tower location, commission rate, and active status.
- **Menu Items:** Create items, set pricing, assign categories (Beverages, Meals, Snacks, Office Essentials), upload images, and toggle immediate availability.
- **Bulk CSV Upload:** Upload standard CSV format to import hundreds of items across all concourse shops in seconds.

### D. Promotional Banners & Coupons Engine
- **Promo Banners:** Create promotional banners with headline, badge, subtitle, image URL, and target shop/category.
- **Coupons:** Configure percentage or flat discount rules, minimum order value, maximum discount cap, and expiry dates.

### E. Masked OTP & Supervisor Reveal Audit
- In normal operation, customer delivery OTPs are masked (`******`) to prevent fraud and premature order completion.
- In exceptional customer disputes, a supervisor can click **"Reveal OTP"** with a mandatory reason note.
- An immutable entry is written to `audit_logs` recording supervisor ID, timestamp, order ID, and reason.

### F. Daily Vendor Settlements
- Review fulfilled child orders per shop.
- Generate settlement vouchers with gross food payable, commission deduction, and net payable.
- Record bank transfer UTR number and mark settlement `PAID`.

