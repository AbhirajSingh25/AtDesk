# AtDesk Quality Assurance & Verification Report

**Date of Execution:** 2026-11-04  
**Environment:** Local Staging (PostgreSQL 18 on 127.0.0.1:5433, Python 3.11, Next.js 14, Android SDK 35)  
**Branch:** `rebuild/role-separation`  

---

## 1. Automated Test Suite Summary (Pytest)

All 27 automated tests executed and passed without regressions:

```
backend/tests/test_atdesk.py::test_create_order PASSED
backend/tests/test_atdesk.py::test_invalid_phone PASSED
backend/tests/test_atdesk.py::test_unauthorized_access PASSED
backend/tests/test_atdesk.py::test_role_based_access PASSED
backend/tests/test_atdesk.py::test_order_status_transitions PASSED
backend/tests/test_atdesk.py::test_otp_verification PASSED
backend/tests/test_atdesk.py::test_invalid_otp PASSED
backend/tests/test_atdesk.py::test_runner_assignment PASSED
backend/tests/test_atdesk.py::test_multi_shop_order PASSED
backend/tests/test_atdesk.py::test_cancel_order PASSED
backend/tests/test_atdesk.py::test_refund_calculation PASSED
backend/tests/test_atdesk.py::test_settlement_ledger PASSED

backend/tests/test_commercial_pilot_validation.py::test_pilot_metrics PASSED
backend/tests/test_commercial_pilot_validation.py::test_pilot_shop_fulfilment PASSED
backend/tests/test_commercial_pilot_validation.py::test_pilot_unit_economics PASSED
backend/tests/test_commercial_pilot_validation.py::test_pilot_reconciliation PASSED
backend/tests/test_commercial_pilot_validation.py::test_pilot_runner_productivity PASSED

backend/tests/test_live_integrations.py::test_payment_signature_verification PASSED
backend/tests/test_live_integrations.py::test_invalid_payment_signature PASSED
backend/tests/test_live_integrations.py::test_dlt_sms_otp_dispatch PASSED
backend/tests/test_live_integrations.py::test_shop_staff_workflow PASSED
backend/tests/test_live_integrations.py::test_shop_item_availability_toggle PASSED
backend/tests/test_live_integrations.py::test_coupon_validation_and_discount PASSED
backend/tests/test_live_integrations.py::test_runner_workload_dispatch PASSED

backend/tests/test_postgresql_concurrency.py::test_concurrent_order_placement PASSED
backend/tests/test_postgresql_concurrency.py::test_row_level_locking_for_update PASSED
backend/tests/test_postgresql_concurrency.py::test_prepaid_balance_atomic_deduction PASSED

======================== 27 passed in 33.64s ========================
```

---

## 2. Frontend Production Build & Static Export

- **Command:** `npm run build`
- **Result:** Success (Exit Code 0).
- **Generated Routes:**
  - `○ /` (Employee Application) — 110 kB First Load JS
  - `○ /admin` (Operations Admin Dashboard) — 101 kB First Load JS
  - `○ /runner` & `/delivery` (Campus Runner Application) — 95.4 kB First Load JS
  - `○ /shop-inbox` (Shop Staff Order Inbox) — 93.4 kB First Load JS

---

## 3. Native Android Build Artifacts

Both flavors compiled with zero errors:

| Artifact Target | Product Flavor | Package ID | Format | File Size | Output Path |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Employee Debug** | `employee` | `com.thesortedclub.atdesk` | APK | 10.46 MB | `frontend/android/app/build/outputs/apk/employee/debug/app-employee-debug.apk` |
| **Runner Debug** | `runner` | `com.thesortedclub.atdesk.runner` | APK | 10.46 MB | `frontend/android/app/build/outputs/apk/runner/debug/app-runner-debug.apk` |
| **Employee Release** | `employee` | `com.thesortedclub.atdesk` | AAB | 7.51 MB | `frontend/android/app/build/outputs/bundle/employeeRelease/app-employee-release.aab` |
| **Runner Release** | `runner` | `com.thesortedclub.atdesk.runner` | AAB | 7.51 MB | `frontend/android/app/build/outputs/bundle/runnerRelease/app-runner-release.aab` |

