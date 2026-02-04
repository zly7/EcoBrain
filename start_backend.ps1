# EcoBrain Backend Startup Script
# Run in VSCode terminal: .\start_backend.ps1

# Set UTF-8 encoding
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

# Configure DeepSeek API
$env:DEEPSEEK_API_KEY = "sk-528ef67fe6c54700b6b9eb31fecff922"
$env:OPENAI_BASE_URL = "https://api.deepseek.com"
$env:OPENAI_MODEL = "deepseek-chat"
$env:OPENAI_MAX_TOKENS = "4000"

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  EcoBrain Backend Starting..."           -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "LLM: DeepSeek API (deepseek-chat)"        -ForegroundColor Yellow
Write-Host ""
Write-Host "Server:  http://localhost:8000"           -ForegroundColor Green
Write-Host "API Doc: http://localhost:8000/docs"      -ForegroundColor Green
Write-Host ""
Write-Host "Press Ctrl+C to stop"                     -ForegroundColor Gray
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Start uvicorn server
python -m uvicorn multi_energy_agent.api.main:app --reload --host 0.0.0.0 --port 8000
