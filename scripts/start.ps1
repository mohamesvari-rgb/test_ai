<#
  Starts the Scientific Evaluation Agent for a demo.

  * Picks the Python prepared by setup.bat (.venv or runtime\python).
  * Starts the local Ollama server in the background if it is installed but
    not running, so OFFLINE mode is ready.
  * Launches the web app and opens it in a clean app window (Edge/Chrome
    without tabs or address bar). Use -Browser to open a normal browser tab.

  Usage (normally via start.bat):
      powershell -ExecutionPolicy Bypass -File scripts\start.ps1 [-Port 5000] [-Browser] [-NoBrowser]
#>
param(
    [int]$Port = 5000,
    [switch]$Browser,
    [switch]$NoBrowser
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$py = $null
foreach ($candidate in @(".venv\Scripts\python.exe", "runtime\python\python.exe")) {
    $full = Join-Path $Root $candidate
    if (Test-Path $full) { $py = $full; break }
}
if (-not $py) {
    Write-Host "Python environment not found. Run setup.bat first." -ForegroundColor Red
    exit 1
}

# --- make the offline engine available, if installed -----------------------
$ollama = Get-Command ollama -ErrorAction SilentlyContinue
if ($ollama) {
    $base = if ($env:OLLAMA_BASE_URL) { $env:OLLAMA_BASE_URL } else { "http://127.0.0.1:11434" }
    $running = $false
    try { Invoke-RestMethod "$base/api/version" -TimeoutSec 2 | Out-Null; $running = $true } catch {}
    if (-not $running) {
        Write-Host "Starting the local Ollama server (offline engine)..." -ForegroundColor Cyan
        Start-Process -FilePath $ollama.Source -ArgumentList "serve" -WindowStyle Hidden
    }
}

$guiArgs = @("gui.py", "--port", "$Port")
if ($NoBrowser) { $guiArgs += "--no-browser" }
elseif (-not $Browser) { $guiArgs += "--app-window" }

& $py @guiArgs
