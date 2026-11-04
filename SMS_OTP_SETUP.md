# Indian DLT SMS OTP Configuration Guide

In accordance with Telecom Regulatory Authority of India (TRAI) guidelines, all commercial transactional SMS messages and One-Time Passwords (OTPs) sent within India must be registered on an approved Distributed Ledger Technology (DLT) platform.

---

## 1. DLT Registration Requirements

To deliver SMS OTPs in India to employee numbers (+91), The Sorted Club must complete DLT registration on any principal telecom portal (e.g. Jio, Airtel, Vodafone Idea, or BSNL DLT).

1. **Entity Registration:**
   - Register Company PAN, Certificate of Incorporation, and GST details.
   - Obtain **Principal Entity ID (PE ID)** (19-digit number, e.g. `1701159876543210987`).
2. **Sender Header Registration:**
   - Type: Transactional / Service Implicit.
   - Header: Exactly 6 alphabetic characters (e.g. `SORTED`).
3. **Content Template Registration:**
   - Type: Service Implicit / Transactional.
   - Template Name: `AtDesk Desk Delivery Login OTP`
   - Registered Text Format:
     ```text
     {#var#} is your verification code for AtDesk by The Sorted Club. Valid for 5 minutes. Do not share this OTP with anyone.
     ```
   - Obtain **Template ID** (19-digit number, e.g. `1707161234567890123`).

---

## 2. Canonical Environment Variables

| Variable Name | Required | Example | Description |
| :--- | :--- | :--- | :--- |
| `SMS_PROVIDER` | **Yes** | `GUPSHUP` or `MSG91` | SMS Gateway adapter. `TEST_MOCK` is strictly forbidden in production. |
| `SMS_API_KEY` | **Yes** | String | Provider API key or authorization token. |
| `SMS_SENDER_ID` | **Yes** | `SORTED` | Registered 6-character sender header. |
| `SMS_DLT_PE_ID` | **Yes** | `1701XXXXXXXXXXXXXXXX` | 19-digit TRAI registered Principal Entity ID. |
| `SMS_DLT_TEMPLATE_ID` | **Yes** | `1707XXXXXXXXXXXXXXXX` | 19-digit TRAI registered OTP Template ID. |
| `SMS_GUPSHUP_USERID` | Optional | String | Gupshup Enterprise Account User ID. |
| `SMS_GUPSHUP_PASSWORD`| Optional | String | Gupshup Enterprise Account Password. |

---

## 3. Real Provider HTTP Integrations

### Option A: Gupshup Enterprise HTTP API
The backend sends an HTTP POST request to:
```
https://enterprise.smsgupshup.com/GatewayAPI/rest
```
Parameters passed:
- `method`: `SendMessage`
- `send_to`: `91<10_digit_mobile>`
- `msg`: Filled DLT template string with 6-digit OTP
- `msg_type`: `TEXT`
- `userid` & `password`: Configured credentials
- `auth_scheme`: `plain`
- `v`: `1.1`
- `format`: `json`
- `principalEntityId`: `SMS_DLT_PE_ID`
- `dltTemplateId`: `SMS_DLT_TEMPLATE_ID`

The provider response must contain `{"response": {"status": "success", "id": "..."}}`. If any error occurs or credentials fail, the backend returns HTTP 400 and does NOT fabricate a successful delivery.

### Option B: MSG91 Flow / OTP API
The backend sends an HTTP POST request to:
```
https://control.msg91.com/api/v5/otp
```
Headers: `{"authkey": "<SMS_API_KEY>", "content-type": "application/json"}`  
Body: `{"template_id": "<SMS_DLT_TEMPLATE_ID>", "mobile": "91<phone>", "otp": "<otp>"}`

The provider response must return HTTP 200 with `{"type": "success"}`.

---

## 4. Production Security & Masking Guarantees

1. **Zero Exposure:** Production OTP codes are NEVER returned in API responses or written to production log files.
2. **Rate Limiting:** Maximum 5 OTP requests per hour per phone number.
3. **Resend Cooldown:** Minimum 60-second cooldown between requests.
4. **Lockout Policy:** Maximum 3 verification attempts before an automatic 15-minute phone lockout.
