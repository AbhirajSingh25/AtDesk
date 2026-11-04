# Build Runner Android APK & Release Bundle
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  AtDesk Runner Android Build (com.thesortedclub.atdesk.runner)  " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

Push-Location frontend
Write-Host "`n[1/3] Building frontend static bundle..." -ForegroundColor Yellow
npm run build
if ($LASTEXITCODE -ne 0) { Pop-Location; exit $LASTEXITCODE }

Write-Host "`n[2/3] Syncing Capacitor Android assets..." -ForegroundColor Yellow
npx cap sync android
if ($LASTEXITCODE -ne 0) { Pop-Location; exit $LASTEXITCODE }

Write-Host "`n[3/3] Compiling Runner Debug APK & Release Bundle..." -ForegroundColor Yellow
Push-Location android
.\gradlew.bat assembleRunnerDebug bundleRunnerRelease
if ($LASTEXITCODE -ne 0) { Pop-Location; Pop-Location; exit $LASTEXITCODE }

Pop-Location
Pop-Location

Write-Host "`nRunner APK Build complete!" -ForegroundColor Green
Write-Host "Debug APK: frontend/android/app/build/outputs/apk/runner/debug/app-runner-debug.apk" -ForegroundColor Green
Write-Host "Release AAB: frontend/android/app/build/outputs/bundle/runnerRelease/app-runner-release.aab" -ForegroundColor Green
