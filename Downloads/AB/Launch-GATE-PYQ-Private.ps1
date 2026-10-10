$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot

if (-not (Get-Command vercel -ErrorAction SilentlyContinue)) {
  Write-Host 'Vercel CLI was not found. Install it with: npm install -g vercel' -ForegroundColor Red
  Read-Host 'Press Enter to close'
  exit 1
}

if (-not (Test-Path (Join-Path $ProjectRoot '.vercel\project.json'))) {
  Write-Host 'This folder must be linked to your Vercel project once before private local mode can run.' -ForegroundColor Yellow
  Write-Host 'Run: vercel link' -ForegroundColor Yellow
  Read-Host 'Press Enter to close'
  exit 1
}

if (-not (Test-Path (Join-Path $ProjectRoot '.env.local'))) {
  Write-Host 'Missing .env.local. Add the Firebase web values and server-only access-control variables locally.' -ForegroundColor Red
  Write-Host 'Never commit .env.local or put server secrets in VITE_* variables.' -ForegroundColor Yellow
  Read-Host 'Press Enter to close'
  exit 1
}

Write-Host 'Starting GATE PYQ Command Center on localhost only: http://127.0.0.1:4173' -ForegroundColor Cyan
Write-Host 'Keep this window open while using the app. This does not deploy the website.' -ForegroundColor Gray
& vercel dev --listen 127.0.0.1:4173
Read-Host 'Local server stopped. Press Enter to close'
