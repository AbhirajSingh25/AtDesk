# Android Build & Play Store Release Guide

This guide covers building, signing, and releasing the two native Android applications for AtDesk:
1. **Employee Application:** `com.thesortedclub.atdesk`
2. **Runner Application:** `com.thesortedclub.atdesk.runner`

---

## 1. Keystore Generation (Do Once)

Generate a private signing keystore for The Sorted Club.

```powershell
keytool -genkey -v -keystore atdesk-release-key.jks -alias atdesk -keyalg RSA -keysize 2048 -validity 10000
```
Store `atdesk-release-key.jks` and its password securely in a password manager. **NEVER commit keystore files to Git.**

---

## 2. Automated Build Scripts

Run the build automation scripts from the repository root:

### Employee App (`com.thesortedclub.atdesk`):
```powershell
.\scripts\build-employee-android.ps1
```
Outputs:
- **Debug APK:** `frontend/android/app/build/outputs/apk/employee/debug/app-employee-debug.apk`
- **Release AAB:** `frontend/android/app/build/outputs/bundle/employeeRelease/app-employee-release.aab`

### Runner App (`com.thesortedclub.atdesk.runner`):
```powershell
.\scripts\build-runner-android.ps1
```
Outputs:
- **Debug APK:** `frontend/android/app/build/outputs/apk/runner/debug/app-runner-debug.apk`
- **Release AAB:** `frontend/android/app/build/outputs/bundle/runnerRelease/app-runner-release.aab`

---

## 3. Signing Release App Bundles (AAB)

Sign the generated release bundles before uploading to Google Play Console:

```powershell
jarsigner -verbose -sigalg SHA256withRSA -digestalg SHA-256 `
  -keystore atdesk-release-key.jks `
  frontend/android/app/build/outputs/bundle/employeeRelease/app-employee-release.aab `
  atdesk

jarsigner -verbose -sigalg SHA256withRSA -digestalg SHA-256 `
  -keystore atdesk-release-key.jks `
  frontend/android/app/build/outputs/bundle/runnerRelease/app-runner-release.aab `
  atdesk
```

---

## 4. Testing Debug APKs on Physical Devices

Connect an Android device via USB and enable USB Debugging:

```powershell
# Install Employee APK
adb install -r frontend/android/app/build/outputs/apk/employee/debug/app-employee-debug.apk

# Install Runner APK
adb install -r frontend/android/app/build/outputs/apk/runner/debug/app-runner-debug.apk
```

Both apps can be installed side-by-side on the same physical phone because they have distinct application IDs (`com.thesortedclub.atdesk` and `com.thesortedclub.atdesk.runner`).
