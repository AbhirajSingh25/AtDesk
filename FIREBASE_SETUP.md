# Firebase Cloud Messaging (FCM) Push Notifications Setup

AtDesk utilizes Firebase Cloud Messaging (FCM) to send real-time push notifications to:
1. **Employees:** Order accepted, runner approaching, desk drop OTP prompt.
2. **Runners:** New delivery assignment, shop order ready for pickup.
3. **Shop Vendors:** New incoming order chime and updates.

---

## 1. Firebase Project & Dual Android App Registration

1. Go to [Firebase Console](https://console.firebase.google.com).
2. Create project: `AtDesk Production`.
3. Register two Android applications in the same project:
   - **Employee App:** Package ID `com.thesortedclub.atdesk`
   - **Runner App:** Package ID `com.thesortedclub.atdesk.runner`
4. Download the separate configuration files and place them into their respective flavor directories:
   - For Employee: `frontend/android/app/src/employee/google-services.json`
   - For Runner: `frontend/android/app/src/runner/google-services.json`
   - (Or place default `google-services.json` at `frontend/android/app/google-services.json`).

Gradle automatically applies the appropriate flavor configuration when compiling `assembleEmployeeDebug`, `assembleRunnerDebug`, `bundleEmployeeRelease`, or `bundleRunnerRelease`.

---

## 2. Server Configuration Variables

| Variable Name | Required | Example | Description |
| :--- | :--- | :--- | :--- |
| `FCM_SERVER_KEY` | Optional | String | Firebase Cloud Messaging server key for sending push notifications. |
| `FCM_PROJECT_ID` | Optional | `atdesk-notifications-pilot` | Firebase project identifier. |
| `FIREBASE_CREDENTIALS_JSON` | Optional | Path / JSON string | Google service account JSON for FCM v1 API. |

---

## 3. Push Delivery & Reactive Polling Fallback

1. **Active Push:** When `FCM_SERVER_KEY` is provided, notifications are pushed directly to registered device tokens via FCM HTTP endpoints with `high` priority.
2. **Database Fallback:** Every notification is simultaneously committed to the PostgreSQL `notifications` table, enabling reactive polling fallback for PWAs and devices with background execution limits.
