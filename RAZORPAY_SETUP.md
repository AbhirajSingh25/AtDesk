# Razorpay Payment Gateway Integration Guide

AtDesk integrates with **Razorpay Standard Checkout** to accept UPI (Google Pay, PhonePe, Paytm, CRED), Net Banking, and Credit/Debit cards.

---

## 1. Razorpay Account Setup

1. Sign in to [Razorpay Dashboard](https://dashboard.razorpay.com).
2. Complete merchant onboarding and Business KYC for **The Sorted Club**.
3. Generate API Keys:
   - Navigate to **Settings** -> **API Keys**.
   - Generate Key for **Test Mode** (during staging) or **Live Mode** (production).
   - Copy `Key Id` (`rzp_live_*` or `rzp_test_*`) and `Key Secret`.

---

## 2. Server-Side Payment Flow

AtDesk uses a strict server-authoritative payment lifecycle:

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
```

---

## 3. Webhook Configuration (Fail-safe Idempotence)

To guarantee order status is updated even if a customer's phone loses connectivity right after payment:

1. Navigate to **Razorpay Dashboard** -> **Settings** -> **Webhooks**.
2. Click **Add New Webhook**.
3. **Webhook URL:** `https://api.atdesk.thesortedclub.com/api/orders/webhook/razorpay`
4. **Secret:** Generate a random 32-character string and set as `RAZORPAY_WEBHOOK_SECRET` in backend environment variables.
5. **Active Events:**
   - `order.paid`
   - `payment.captured`
   - `payment.failed`
   - `refund.processed`

The webhook handler verifies `X-Razorpay-Signature` using `RAZORPAY_WEBHOOK_SECRET` before processing status transitions.

---

## 4. Refund Engine

When an order is cancelled within the 2-minute grace window or rejected by shops:
- The backend issues a refund via Razorpay Refunds API:
  ```python
  client.payment.refund(payment_id, {
      "amount": int(total_amount * 100),
      "speed": "optimum",
      "notes": {"reason": "Customer cancelled within 2-min grace window"}
  })
  ```
- An audit log and refund ledger entry are created in the database.
