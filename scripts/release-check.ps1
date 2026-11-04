# End-to-end Release Verification Gate
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  AtDesk Production Release Verification  " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# 1. Check production configuration audit
Write-Host "`n[Check 1/4] Auditing production configuration template..." -ForegroundColor Yellow
python scripts/check-production-config.py

# 2. Run backend automated tests
Write-Host "`n[Check 2/4] Running Backend Pytest Suite..." -ForegroundColor Yellow
$env:PYTHONPATH = "."
py -3.11 -m pytest backend/tests/ -v
if ($LASTEXITCODE -ne 0) {
    Write-Host "Backend tests failed!" -ForegroundColor Red
    exit $LASTEXITCODE
}

# 3. Check frontend production build
Write-Host "`n[Check 3/4] Verifying Next.js Production Build..." -ForegroundColor Yellow
Push-Location frontend
npm run build
if ($LASTEXITCODE -ne 0) {
    Pop-Location
    Write-Host "Frontend build failed!" -ForegroundColor Red
    exit $LASTEXITCODE
}
Pop-Location

# 4. Verify Android outputs exist
Write-Host "`n[Check 4/4] Verifying Android App Artifacts..." -ForegroundColor Yellow
$employeeApk = "frontend/android/app/build/outputs/apk/employee/debug/app-employee-debug.apk"
$runnerApk = "frontend/android/app/build/outputs/apk/runner/debug/app-runner-debug.apk"

if (Test-Path $employeeApk) {
    $emp = Get-Item $employeeApk
    Write-Host " [PASS] Employee Debug APK: $($emp.Length) bytes ($($emp.FullName))" -ForegroundColor Green
} else {
    Write-Host " [FAIL] Employee Debug APK not found. Run scripts/build-employee-android.ps1" -ForegroundColor Red
}

if (Test-Path $runnerApk) {
    $run = Get-Item $runnerApk
    Write-Host " [PASS] Runner Debug APK: $($run.Length) bytes ($($run.FullName))" -ForegroundColor Green
} else {
    Write-Host " [FAIL] Runner Debug APK not found. Run scripts/build-runner-android.ps1" -ForegroundColor Red
}

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  Release Verification Complete!         " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
