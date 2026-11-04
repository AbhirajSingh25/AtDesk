# Razorpay Payment Gateway & Webhook Guide

AtDesk integrates with **Razorpay Standard Checkout** to accept UPI (Google Pay, PhonePe, Paytm, CRED), Net Banking, and Credit/Debit cards.

---

## 1. Razorpay Account Setup

1. Sign in to [Razorpay Dashboard](https://dashboard.razorpay.com).
2. Complete merchant onboarding and Business KYC for **The Sorted Club**.
3. Generate API Keys:
   - Navigate to **Settings** -> **API Keys**.
   - Generate Key for **Test Mode** (during staging) or **Live Mode** (production).
   - Set environment variables:
     - `RAZORPAY_KEY_ID`: `rzp_live_*` (or `rzp_test_*`)
     - `RAZORPAY_KEY_SECRET`: Secret key

---

## 2. Mandatory Webhook Verification & Configuration

To guarantee orders are confirmed even if a customer's phone loses connectivity right after payment:

1. Navigate to **Razorpay Dashboard** -> **Settings** -> **Webhooks**.
2. Click **Add New Webhook**.
3. **Canonical Webhook URL:**
   ```
   https://api.atdesk.thesortedclub.com/api/payments/razorpay/webhook
   ```
   *(Note: `/api/payments/webhook` is also routed identically for backwards compatibility).*
4. **Secret:** Set a random 32-character string and configure it as `RAZORPAY_WEBHOOK_SECRET` in your backend environment variables.
5. **Alert Email:** Enter your operations email (e.g. `ops@thesortedclub.com`).
6. **Active Events:**
   - `order.paid`
   - `payment.captured`
   - `payment.failed`
   - `refund.processed`

### Webhook Security Enforcements:
- **Mandatory Header:** The backend requires `X-Razorpay-Signature`. Requests with missing or invalid signatures are immediately rejected with **HTTP 400 Bad Request**.
- **HMAC SHA-256 Validation:** Verifies raw payload bytes against `RAZORPAY_WEBHOOK_SECRET`.
- **Currency & Amount Check:** Confirms `currency == "INR"` and matches payload amount (paise to INR) against the database payment record.
- **Idempotency:** Duplicate events for the same `gateway_payment_id` are acknowledged with `status: ok` without duplicate side-effects.

---

## 3. Server-Authoritative Order & Refund Lifecycle

```
[Employee App]          [AtDesk FastAPI]               [Razorpay Gateway]
      │                         │                              │
      │── 1. Create Order ─────>│                              │
      │                         │── 2. Create Order API ──────>│
      │                         │<── Returns `rzp_order_id` ───│
      │<── Returns Order Info ──│                              │
      │                                                        │
      │── 3. Open Razorpay Checkout Modal ────────────────────>│
      │      (User completes UPI/Card payment)                 │
      │<── 4. Handler callback (payment_id, signature) ────────│
      │                                                        │
      │── 5. Verify Signature ─>│                              │
      │                         │── 6. HMAC-SHA256 Check ──────│
      │                         │   (Matches secret?)          │
      │                         │   -> Marks Order `PAID`      │
      │                         │   -> Dispatches to Shops     │
      │<── 7. Order Confirmed ──│                              │
      │                                                        │
      │                                [Razorpay Webhook Event]│
      │                         │<─── order.paid / captured ───│
      │                         │─── 8. Mandatory HMAC check ──│
      │                         │─── 9. Idempotent DB update ──│
```

---

## 4. Refund Engine

When an order is cancelled within the 2-minute grace window or rejected by a shop:
- The backend initiates a refund via Razorpay Refunds API:
  ```python
  client.payment.refund(payment_id, {
      "amount": int(total_amount * 100),
      "notes": {"reason": "Customer cancelled within 2-min window"}
  })
  ```
- If the payment provider fails or returns an error in production, the backend logs the error and returns `status: FAILED` instead of silently fabricating refund success.
