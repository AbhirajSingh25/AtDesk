# Indian DLT SMS OTP Configuration Guide

In accordance with Telecom Regulatory Authority of India (TRAI) guidelines, all commercial transactional SMS messages and One-Time Passwords (OTPs) sent within India must be registered on an approved Distributed Ledger Technology (DLT) platform.

---

## 1. DLT Registration Overview

To deliver SMS OTPs in India to employee numbers (+91), The Sorted Club must complete DLT registration on any principal telecom portal (e.g. Jio, Airtel, Vodafone Idea, or BSNL DLT).

1. **Entity Registration:**
   - Register Company PAN, Certificate of Incorporation, and GST details.
   - Obtain Entity ID / PE ID (e.g. `1401XXXXXXXXXXXX`).
2. **Sender ID (Header) Registration:**
   - Type: Transactional / Service Implicit.
   - Header: 6 alphabetic characters (e.g. `SORTED` or `ATDESK`).
3. **Content Template Registration:**
   - Type: Service Implicit / Transactional.
   - Template Category: OTP / Authentication.
   - Template Name: `AtDesk Desk Delivery Login OTP`
   - Registered Text:
     ```text
     {#var#} is your verification code for AtDesk by The Sorted Club. Valid for 5 minutes. Do not share this OTP with anyone.
     ```
   - Obtain Template ID (e.g. `1107XXXXXXXXXXXX`).

---

## 2. Supported SMS Providers

AtDesk supports Gupshup Enterprise SMS API and MSG91 Flow API.

### Option A: Gupshup Integration
Set the following environment variables:
```bash
SMS_GATEWAY_PROVIDER="GUPSHUP"
SMS_GATEWAY_API_KEY="your_gupshup_auth_token"
DLT_OTP_TEMPLATE_ID="1107XXXXXXXXXXXX"
DLT_SENDER_ID="SORTED"
```

The backend sends a POST request to Gupshup Enterprise REST API:
```text
https://enterprise.smsgupshup.com/GatewayAPI/rest?method=SendMessage&send_to=91<PHONE>&msg=<MSG>&userid=<USERID>&auth_scheme=plain&password=<PASSWORD>&v=1.1&format=json&msg_type=TEXT
```

### Option B: MSG91 Integration
Set the following environment variables:
```bash
SMS_GATEWAY_PROVIDER="MSG91"
SMS_GATEWAY_API_KEY="your_msg91_authkey"
DLT_OTP_TEMPLATE_ID="1107XXXXXXXXXXXX"
DLT_SENDER_ID="SORTED"
```

---

## 3. Rate Limiting & Fraud Prevention

To prevent OTP spam and SMS pumping fraud:
- Maximum 3 OTP requests per phone number per 15 minutes.
- Fixed 5-minute expiry per OTP token.
- Immediate invalidation upon successful login.
- IP rate limiting: 10 OTP requests per minute per IP address.
