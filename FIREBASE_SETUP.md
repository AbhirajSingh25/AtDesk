# Firebase Cloud Messaging (FCM) Push Notifications Setup

AtDesk utilizes Firebase Cloud Messaging (FCM) to send real-time push notifications to:
1. **Employees:** Order accepted, out for delivery, runner arrived at desk with OTP.
2. **Runners:** New delivery task assignment, shop order ready for pickup.
3. **Shop Vendors:** New incoming order chime/notification.

---

## 1. Firebase Project Creation

1. Go to [Firebase Console](https://console.firebase.google.com).
2. Create project: `AtDesk Production`.
3. Add two Android applications to the project:
   - Application 1: `com.thesortedclub.atdesk` (Employee App)
   - Application 2: `com.thesortedclub.atdesk.runner` (Runner App)
4. Download the `google-services.json` configuration file.
5. Place `google-services.json` into:
   ```
   frontend/android/app/google-services.json
   ```

---

## 2. Server Account Credentials

1. In Firebase Console, go to **Project Settings** -> **Service accounts**.
2. Click **Generate new private key**.
3. Save the resulting JSON file securely.
4. Set the path or json contents in the backend environment:
   ```bash
   FIREBASE_CREDENTIALS_JSON="/path/to/firebase-service-account.json"
   ```

---

## 3. Notification Payloads & Deep Linking

FCM notifications are delivered with high priority to ensure instant wakeups:

```json
{
  "message": {
    "token": "device_registration_token",
    "notification": {
      "title": "Order #1042 Arrived at Your Desk!",
      "body": "Your runner is at Tower B, Floor 6. Give OTP 849201 to receive your order."
    },
    "data": {
      "order_id": "1042",
      "action": "ORDER_TRACKING",
      "url": "/order/1042"
    },
    "android": {
      "priority": "high",
      "notification": {
        "channel_id": "atdesk_orders",
        "sound": "order_bell",
        "click_action": "FLUTTER_NOTIFICATION_CLICK"
      }
    }
  }
}
```
