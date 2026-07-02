# WhisprLocal one-command bootstrap (Windows / PowerShell)
#
#   powershell -ExecutionPolicy Bypass -File .\setup.ps1
#
# Creates a per-machine virtualenv, installs the app + the optional local-LLM
# cleanup runtime (AVX2-safe wheel, runs on any x86-64 CPU), downloads the LLM
# model, and writes a starter config with semantic cleanup enabled.
#
#   -NoLlm   base voice dictation only (skip the LLM runtime + model download)
[CmdletBinding()]
param([switch]$NoLlm)

$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot   # project root = folder this script lives in

Write-Host "==> WhisprLocal setup (in $PSScriptRoot)" -ForegroundColor Cyan

# --- 1. Find a Python to bootstrap the venv --------------------------------
if (Get-Command py -ErrorAction SilentlyContinue) {
    $boot = 'py'; $bootArgs = @('-3')
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $boot = 'python'; $bootArgs = @()
} else {
    throw "No Python found. Install Python 3.11+ from https://python.org and re-run."
}

# --- 2. Create the virtualenv (idempotent) ---------------------------------
$venvPy = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path $venvPy)) {
    Write-Host "==> Creating virtualenv (.venv)" -ForegroundColor Cyan
    & $boot @bootArgs -m venv .venv
} else {
    Write-Host "==> Reusing existing .venv" -ForegroundColor Cyan
}

# --- 3. Install the app ----------------------------------------------------
Write-Host "==> Installing WhisprLocal + dependencies" -ForegroundColor Cyan
& $venvPy -m pip install --upgrade pip
& $venvPy -m pip install -e .

# --- 4. Optional: local-LLM cleanup runtime + model ------------------------
if (-not $NoLlm) {
    Write-Host "==> Installing local-LLM runtime (AVX2-safe wheel)" -ForegroundColor Cyan
    # PyPI wheels are AVX-512 and crash on CPUs without it (e.g. Comet Lake).
    # The pinned wheel from the CPU index is AVX2-only and runs everywhere.
    & $venvPy -m pip install "llama-cpp-python==0.2.90" `
        --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu

    Write-Host "==> Downloading LLM model (~1 GB, one time)" -ForegroundColor Cyan
    & $venvPy -c @"
import os
from huggingface_hub import hf_hub_download
d = os.path.expanduser('~/.cache/whisprlocal')
os.makedirs(d, exist_ok=True)
p = hf_hub_download('Qwen/Qwen2.5-1.5B-Instruct-GGUF',
                    'qwen2.5-1.5b-instruct-q4_k_m.gguf', local_dir=d)
print('  model at', p)
"@
}

# --- 5. Starter config (don't clobber an existing one) ---------------------
$cfgDir  = Join-Path $HOME '.config\whisprlocal'
$cfgPath = Join-Path $cfgDir 'config.toml'
if (-not (Test-Path $cfgPath)) {
    Write-Host "==> Writing starter config to $cfgPath" -ForegroundColor Cyan
    New-Item -ItemType Directory -Force $cfgDir | Out-Null
    $cfg = Get-Content (Join-Path $PSScriptRoot 'config.example.toml') -Raw
    if (-not $NoLlm) { $cfg = $cfg -replace 'llm_cleanup = false', 'llm_cleanup = true' }
    Set-Content -Path $cfgPath -Value $cfg -Encoding utf8
} else {
    Write-Host "==> Keeping existing config at $cfgPath" -ForegroundColor Cyan
}

Write-Host ""
Write-Host "Done. To run:" -ForegroundColor Green
Write-Host "  .\.venv\Scripts\python.exe -m whisprlocal"
Write-Host "Then hold Ctrl+Alt, speak, release."
Write-Host "To start on login (no window): put a shortcut to whisprlocal-autostart.vbs"
Write-Host "  in your Startup folder (Win+R -> shell:startup)."
