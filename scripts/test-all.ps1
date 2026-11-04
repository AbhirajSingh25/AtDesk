# Run full test suite for AtDesk backend and frontend
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  AtDesk End-to-End Test Suite Runner  " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

$env:PYTHONPATH = "."
Write-Host "`n[1/2] Running Backend Pytest Suite..." -ForegroundColor Yellow
py -3.11 -m pytest backend/tests/ -v
if ($LASTEXITCODE -ne 0) {
    Write-Host "`nBackend tests failed!" -ForegroundColor Red
    exit $LASTEXITCODE
}
Write-Host "`nBackend tests passed successfully!" -ForegroundColor Green

Write-Host "`n[2/2] Running Frontend Typecheck & Build..." -ForegroundColor Yellow
Push-Location frontend
npm run build
if ($LASTEXITCODE -ne 0) {
    Pop-Location
    Write-Host "`nFrontend build failed!" -ForegroundColor Red
    exit $LASTEXITCODE
}
Pop-Location
Write-Host "`nFrontend build & static export passed successfully!" -ForegroundColor Green

Write-Host "`nAll AtDesk test suites and builds passed!" -ForegroundColor Cyan

