<#
  One-time setup for the Scientific Evaluation Agent on Windows.

  * Uses an existing Python 3.10+ if one is installed (creates .venv), otherwise
    downloads a private, portable Python into .\runtime\python (no admin rights,
    nothing installed system-wide).
  * Installs the Python packages from requirements.txt.
  * Creates .env from .env.example on first run.

  Usage (normally via setup.bat):
      powershell -ExecutionPolicy Bypass -File scripts\setup.ps1
      ... -PipIndex https://<mirror>/simple   # use a PyPI mirror if pypi.org is slow/blocked
      ... -Portable                           # always use the portable Python
#>
param(
    [string]$PipIndex = $env:PIP_INDEX_URL,
    [switch]$Portable,
    [string]$PythonVersion = "3.12.10"
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

function Write-Step($msg) { Write-Host "`n==> $msg" -ForegroundColor Cyan }
function Write-Ok($msg)   { Write-Host "    $msg" -ForegroundColor Green }
function Write-Warn2($msg){ Write-Host "    $msg" -ForegroundColor Yellow }

function Test-PythonOk([string]$exe, [string[]]$prefix = @()) {
    try {
        $v = & $exe @prefix -c "import sys; print('%d.%d' % sys.version_info[:2])" 2>$null
        if ($LASTEXITCODE -ne 0 -or -not $v) { return $false }
        $parts = $v.Trim().Split(".")
        return ([int]$parts[0] -eq 3 -and [int]$parts[1] -ge 10)
    } catch { return $false }
}

function Get-PortablePython {
    $target = Join-Path $Root "runtime\python"
    $exe = Join-Path $target "python.exe"
    if (Test-Path $exe) { return $exe }

    Write-Step "Downloading portable Python $PythonVersion (about 15 MB)"
    $tmp = Join-Path $env:TEMP ("sci_eval_py_" + [guid]::NewGuid().ToString("N"))
    New-Item -ItemType Directory -Force $tmp | Out-Null
    $pkg = Join-Path $tmp "python.zip"
    $url = "https://api.nuget.org/v3-flatcontainer/python/$PythonVersion/python.$PythonVersion.nupkg"
    try {
        curl.exe -L --fail --silent --show-error -o $pkg $url
        if ($LASTEXITCODE -ne 0) { throw "curl exit code $LASTEXITCODE" }
    } catch {
        Invoke-WebRequest -Uri $url -OutFile $pkg -UseBasicParsing
    }
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $unz = Join-Path $tmp "x"
    [System.IO.Compression.ZipFile]::ExtractToDirectory($pkg, $unz)
    New-Item -ItemType Directory -Force (Split-Path $target) | Out-Null
    Move-Item (Join-Path $unz "tools") $target
    Remove-Item -Recurse -Force $tmp -ErrorAction SilentlyContinue
    if (-not (Test-Path $exe)) { throw "Portable Python was not extracted correctly." }
    Write-Ok "Portable Python ready: $exe"
    return $exe
}

# ---------------------------------------------------------------- python
Write-Step "Locating Python"
$py = $null
$venvPy = Join-Path $Root ".venv\Scripts\python.exe"
$portablePy = Join-Path $Root "runtime\python\python.exe"

if (Test-Path $venvPy) {
    $py = $venvPy; Write-Ok "Using existing virtual environment (.venv)"
} elseif (Test-Path $portablePy) {
    $py = $portablePy; Write-Ok "Using portable Python (runtime\python)"
} elseif (-not $Portable) {
    $base = $null
    if ((Get-Command py -ErrorAction SilentlyContinue) -and (Test-PythonOk "py" @("-3"))) { $base = @("py", "-3") }
    elseif ((Get-Command python -ErrorAction SilentlyContinue) -and (Test-PythonOk "python")) { $base = @("python") }
    if ($base) {
        Write-Ok "Found system Python; creating .venv"
        $baseArgs = @()
        if ($base.Count -gt 1) { $baseArgs = $base[1..($base.Count - 1)] }
        & $base[0] @baseArgs -m venv .venv
        if ($LASTEXITCODE -ne 0) { throw "Could not create the virtual environment." }
        $py = $venvPy
    }
}
if (-not $py) { $py = Get-PortablePython }

# ---------------------------------------------------------------- packages
Write-Step "Installing Python packages (first run takes a few minutes)"
# Generous timeout/retries: downloads from files.pythonhosted.org can be slow
# or drop out on some networks.
$pipArgs = @("-m", "pip", "install", "--disable-pip-version-check",
             "--timeout", "120", "--retries", "10", "-r", "requirements.txt")
if ($PipIndex) {
    $pipArgs += @("--index-url", $PipIndex)
    Write-Ok "Using package index: $PipIndex"
}
& $py -m pip --version *> $null
if ($LASTEXITCODE -ne 0) { & $py -m ensurepip --upgrade }
# A dropped connection in the middle of dependency resolution makes pip report
# a bogus "conflict"; already-downloaded packages are reused, so just retry.
for ($attempt = 1; $attempt -le 3; $attempt++) {
    & $py @pipArgs
    if ($LASTEXITCODE -eq 0) { break }
    if ($attempt -lt 3) { Write-Warn2 "pip failed (attempt $attempt of 3), retrying..." }
}
if ($LASTEXITCODE -ne 0) {
    Write-Warn2 "Package installation failed. If pypi.org is blocked or slow on your network,"
    Write-Warn2 "re-run with a PyPI mirror:  setup.bat -PipIndex https://<mirror>/simple"
    exit 1
}
Write-Ok "Packages installed."

# ---------------------------------------------------------------- .env
if (-not (Test-Path (Join-Path $Root ".env"))) {
    Copy-Item (Join-Path $Root ".env.example") (Join-Path $Root ".env")
    Write-Ok "Created .env (put your API key there)."
}

# ---------------------------------------------------------------- ollama
Write-Step "Checking the offline engine (Ollama)"
$ollama = Get-Command ollama -ErrorAction SilentlyContinue
if ($ollama) {
    Write-Ok "Ollama is installed: $($ollama.Source)"
    Write-Ok "To download the offline model run:  install_offline_model.bat"
} else {
    Write-Warn2 "Ollama is not installed (only needed for OFFLINE mode)."
    Write-Warn2 "Download: https://ollama.com/download/windows"
    Write-Warn2 "Then run:  install_offline_model.bat"
}

Write-Host "`nSetup complete. Start the demo with:  start.bat`n" -ForegroundColor Green
