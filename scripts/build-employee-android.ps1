# Build Employee Android APK & Release Bundle
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  AtDesk Employee Android Build (com.thesortedclub.atdesk)  " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

Push-Location frontend
Write-Host "`n[1/3] Building frontend static bundle..." -ForegroundColor Yellow
npm run build
if ($LASTEXITCODE -ne 0) { Pop-Location; exit $LASTEXITCODE }

Write-Host "`n[2/3] Syncing Capacitor Android assets..." -ForegroundColor Yellow
npx cap sync android
if ($LASTEXITCODE -ne 0) { Pop-Location; exit $LASTEXITCODE }

Write-Host "`n[3/3] Compiling Employee Debug APK & Release Bundle..." -ForegroundColor Yellow
Push-Location android
.\gradlew.bat assembleEmployeeDebug bundleEmployeeRelease
if ($LASTEXITCODE -ne 0) { Pop-Location; Pop-Location; exit $LASTEXITCODE }

Pop-Location
Pop-Location

Write-Host "`nEmployee APK Build complete!" -ForegroundColor Green
Write-Host "Debug APK: frontend/android/app/build/outputs/apk/employee/debug/app-employee-debug.apk" -ForegroundColor Green
Write-Host "Release AAB: frontend/android/app/build/outputs/bundle/employeeRelease/app-employee-release.aab" -ForegroundColor Green

