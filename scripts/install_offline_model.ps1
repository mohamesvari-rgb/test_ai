<#
  Prepares OFFLINE mode: checks Ollama and downloads (or imports) the local model.

  Usage (normally via install_offline_model.bat):
      ... install_offline_model.ps1                       # default model (qwen3.5:9b, ~6.6 GB)
      ... install_offline_model.ps1 -Model qwen3.5:4b     # smaller/faster (~3.4 GB)
      ... install_offline_model.ps1 -Gguf D:\models\x.gguf -Model my-model
                                                          # import a GGUF file you downloaded
                                                          # elsewhere (when the Ollama registry
                                                          # is unreachable)

  After the model is in place, the agent runs with NO internet connection.
#>
param(
    [string]$Model = "",
    [string]$Gguf = ""
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

function Get-EnvValue([string]$name) {
    $envFile = Join-Path $Root ".env"
    if (-not (Test-Path $envFile)) { return "" }
    $line = Get-Content $envFile -Encoding UTF8 | Where-Object { $_ -match "^\s*$name\s*=" } | Select-Object -First 1
    if ($line) { return ($line -split "=", 2)[1].Trim() }
    return ""
}

function Set-EnvValue([string]$name, [string]$value) {
    $envFile = Join-Path $Root ".env"
    if (-not (Test-Path $envFile)) { Copy-Item (Join-Path $Root ".env.example") $envFile }
    $lines = @(Get-Content $envFile -Encoding UTF8)
    $found = $false
    for ($i = 0; $i -lt $lines.Count; $i++) {
        if ($lines[$i] -match "^\s*#?\s*$name\s*=") { $lines[$i] = "$name=$value"; $found = $true; break }
    }
    if (-not $found) { $lines += "$name=$value" }
    [System.IO.File]::WriteAllLines($envFile, $lines, (New-Object System.Text.UTF8Encoding($false)))
}

if (-not $Model) { $Model = Get-EnvValue "OLLAMA_MODEL" }
if (-not $Model) { $Model = "qwen3.5:9b" }

# --- 1. Ollama installed? ---------------------------------------------------
$ollama = Get-Command ollama -ErrorAction SilentlyContinue
if (-not $ollama) {
    $default = Join-Path $env:LOCALAPPDATA "Programs\Ollama\ollama.exe"
    if (Test-Path $default) { $ollama = Get-Item $default }
}
if (-not $ollama) {
    Write-Host "Ollama is not installed." -ForegroundColor Yellow
    Write-Host "  Official download : https://ollama.com/download/windows"
    Write-Host "  Mirror (GitHub)   : https://github.com/ollama/ollama/releases/latest/download/OllamaSetup.exe"
    Write-Host "Install it, then run install_offline_model.bat again."
    $answer = Read-Host "Open the download page now? [Y/n]"
    if ($answer -ne "n") { Start-Process "https://ollama.com/download/windows" }
    exit 1
}
$exe = if ($ollama.Source) { $ollama.Source } else { $ollama.FullName }
Write-Host "Ollama found: $exe" -ForegroundColor Green

# --- 2. server running? -----------------------------------------------------
$base = if ($env:OLLAMA_BASE_URL) { $env:OLLAMA_BASE_URL } else { "http://127.0.0.1:11434" }
$running = $false
try { Invoke-RestMethod "$base/api/version" -TimeoutSec 2 | Out-Null; $running = $true } catch {}
if (-not $running) {
    Write-Host "Starting the Ollama server..." -ForegroundColor Cyan
    Start-Process -FilePath $exe -ArgumentList "serve" -WindowStyle Hidden
    for ($i = 0; $i -lt 30 -and -not $running; $i++) {
        Start-Sleep -Seconds 1
        try { Invoke-RestMethod "$base/api/version" -TimeoutSec 2 | Out-Null; $running = $true } catch {}
    }
    if (-not $running) { Write-Host "The Ollama server did not start." -ForegroundColor Red; exit 1 }
}

# --- 3. model ---------------------------------------------------------------
if ($Gguf) {
    if (-not (Test-Path $Gguf)) { Write-Host "File not found: $Gguf" -ForegroundColor Red; exit 1 }
    $modelfile = Join-Path $env:TEMP "sci_eval_Modelfile"
    "FROM `"$((Resolve-Path $Gguf).Path)`"" | Set-Content -Encoding ASCII $modelfile
    Write-Host "Importing $Gguf as '$Model' ..." -ForegroundColor Cyan
    & $exe create $Model -f $modelfile
} else {
    Write-Host "Downloading model '$Model' (one time; can take a while) ..." -ForegroundColor Cyan
    Write-Host "Tip: to store models on another drive, change 'Model location' in the Ollama app's Settings first (e.g. D:\ollama-models)."
    & $exe pull $Model
}
if ($LASTEXITCODE -ne 0) {
    Write-Host "Could not get the model. If the Ollama registry is unreachable on your network," -ForegroundColor Yellow
    Write-Host "download a GGUF file of the model elsewhere and import it with:" -ForegroundColor Yellow
    Write-Host "  install_offline_model.bat -Gguf <path-to-file.gguf> -Model <name>" -ForegroundColor Yellow
    exit 1
}

Set-EnvValue "OLLAMA_MODEL" $Model
Write-Host "`nOffline model ready: $Model  (saved to .env as OLLAMA_MODEL)" -ForegroundColor Green
Write-Host "Start the app with start.bat and choose Offline in the AI engine section."
