# Simple HTTP server to run the search interface
# This avoids CORS issues when opening HTML files directly

Write-Host "Starting local web server..." -ForegroundColor Green
Write-Host "Open your browser and go to: http://localhost:8000/search.html" -ForegroundColor Yellow
Write-Host "Press Ctrl+C to stop the server" -ForegroundColor Gray
Write-Host ""

# Change to the script's directory
Set-Location $PSScriptRoot

# Start Python HTTP server
python -m http.server 8000

