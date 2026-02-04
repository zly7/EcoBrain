# EcoBrain Frontend Startup Script
# Run in VSCode terminal: .\start_frontend.ps1

# Set UTF-8 encoding
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  EcoBrain Frontend Starting..."          -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Frontend: http://localhost:3000"          -ForegroundColor Green
Write-Host "Backend:  http://localhost:8000"          -ForegroundColor Yellow
Write-Host ""
Write-Host "Make sure backend is running first!"      -ForegroundColor Gray
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Change to frontend directory
Set-Location -Path "$PSScriptRoot\frontend"

# Check if node_modules exists
if (-not (Test-Path "node_modules")) {
    Write-Host "Installing dependencies..." -ForegroundColor Yellow
    npm install
}

# Start dev server
npm run dev
