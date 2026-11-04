# Google Play Store Submission Checklist

This document details all requirements and assets necessary for publishing AtDesk to Google Play.

---

## 1. Application Packages

| App Name | Package ID | Primary Category |
| :--- | :--- | :--- |
| **AtDesk** | `com.thesortedclub.atdesk` | Food & Drink |
| **AtDesk Runner** | `com.thesortedclub.atdesk.runner` | Business / Tools |

---

## 2. Target SDK & Technical Requirements

- **Target SDK Version:** Android 34 / 35 (Meets Google Play target SDK policy).
- **Minimum SDK Version:** Android 24 (Android 7.0 Nougat) — covers 96%+ active Android devices in India.
- **Architectures:** `arm64-v8a`, `armeabi-v7a`, `x86_64`.
- **Format:** Android App Bundle (`.aab`).

---

## 3. Required App Permissions & Justifications

### Employee App (`com.thesortedclub.atdesk`):
1. `android.permission.INTERNET`: Required to communicate with AtDesk API and process Razorpay payments.
2. `android.permission.ACCESS_NETWORK_STATE`: Required to detect online/offline state and connectivity dropouts.
3. `android.permission.POST_NOTIFICATIONS`: Required on Android 13+ to send live order status alerts.

### Runner App (`com.thesortedclub.atdesk.runner`):
1. `android.permission.CAMERA`: **Mandatory.** Required to take physical photo proof of the delivered package at the customer's desk.
2. `android.permission.ACCESS_FINE_LOCATION` & `ACCESS_COARSE_LOCATION`: Required to verify runner is physically within JMD Megapolis campus (`28.4162° N, 77.0425° E`) during order fulfillment.
3. `android.permission.POST_NOTIFICATIONS`: Required for incoming job alerts and order readiness pings.
4. `android.permission.VIBRATE`: Haptic feedback when new order is assigned.

---

## 4. Google Play Data Safety Declaration

- **Location Data:** Collected in Runner App only to verify campus delivery proximity. Not shared with third parties.
- **Photos & Videos:** Collected in Runner App for delivery verification proof. Uploaded securely to private S3/R2 storage.
- **Personal Info:** Name and Phone Number collected for customer account creation, SMS OTP verification, and desk delivery communication.
- **Financial Info:** Handled directly by PCI-DSS Level 1 compliant gateway (Razorpay). AtDesk does not store credit/debit card numbers or CVV.

---

## 5. Store Listing Assets Checklist

- [ ] App Icon (512x512 PNG, 32-bit with alpha).
- [ ] Feature Graphic (1024x500 JPEG/PNG).
- [ ] Phone Screenshots (At least 4 screenshots, 16:9 or 9:16 aspect ratio).
- [ ] Privacy Policy URL (`https://atdesk.thesortedclub.com/privacy`).
- [ ] Terms of Service URL (`https://atdesk.thesortedclub.com/terms`).
- [ ] Support Email (`support@thesortedclub.com`).

