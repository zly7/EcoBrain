# EcoBrain Backend Startup Script
# Run in VSCode terminal: .\start_backend.ps1

# Set UTF-8 encoding
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

# Configure Xiaomi API (OpenAI compatible)
$env:OPENAI_API_KEY = "sk-cd8fqe8x34tti4t4tfw9d8ktss9pg5l3eq3d2u0dmf0h3lco"
$env:OPENAI_BASE_URL = "https://api.xiaomimimo.com/v1"
$env:OPENAI_MODEL = "mimo-v2-flash"
$env:OPENAI_MAX_TOKENS = "4000"

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  EcoBrain Backend Starting..."           -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "LLM: Xiaomi API (mimo-v2-flash)"          -ForegroundColor Yellow
Write-Host ""
Write-Host "Server:  http://localhost:8000"           -ForegroundColor Green
Write-Host "API Doc: http://localhost:8000/docs"      -ForegroundColor Green
Write-Host ""
Write-Host "Press Ctrl+C to stop"                     -ForegroundColor Gray
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Start uvicorn server
python -m uvicorn multi_energy_agent.api.main:app --reload --host 0.0.0.0 --port 8000
