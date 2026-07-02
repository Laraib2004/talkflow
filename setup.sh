#!/usr/bin/env bash
# WhisprLocal one-command bootstrap (macOS / Linux)
#
#   ./setup.sh            full install (app + local-LLM cleanup + model)
#   ./setup.sh --no-llm   base voice dictation only
#
# Creates a per-machine virtualenv, installs the app + the optional local-LLM
# cleanup runtime, downloads the LLM model, and writes a starter config with
# semantic cleanup enabled.
set -euo pipefail

# Project root = folder this script lives in
cd "$(dirname "$0")"

WITH_LLM=1
[ "${1:-}" = "--no-llm" ] && WITH_LLM=0

echo "==> WhisprLocal setup (in $(pwd))"

# --- 1. Find a Python to bootstrap the venv --------------------------------
if command -v python3 >/dev/null 2>&1; then BOOT=python3
elif command -v python >/dev/null 2>&1; then BOOT=python
else echo "No Python found. Install Python 3.11+ and re-run." >&2; exit 1
fi

# --- 2. Create the virtualenv (idempotent) ---------------------------------
VENV_PY="./.venv/bin/python"
if [ ! -x "$VENV_PY" ]; then
    echo "==> Creating virtualenv (.venv)"
    "$BOOT" -m venv .venv
else
    echo "==> Reusing existing .venv"
fi

# --- 3. Install the app ----------------------------------------------------
echo "==> Installing WhisprLocal + dependencies"
"$VENV_PY" -m pip install --upgrade pip
"$VENV_PY" -m pip install -e .

# Portability reminder: PortAudio is a system lib.
#   macOS:  brew install portaudio
#   Debian: sudo apt install portaudio19-dev libportaudio2

# --- 4. Optional: local-LLM cleanup runtime + model ------------------------
if [ "$WITH_LLM" = "1" ]; then
    echo "==> Installing local-LLM runtime"
    # On a CPU without AVX-512, if this build crashes with an illegal-instruction
    # error, reinstall from the AVX2 CPU index:
    #   pip install "llama-cpp-python==0.2.90" \
    #     --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu
    "$VENV_PY" -m pip install llama-cpp-python

    echo "==> Downloading LLM model (~1 GB, one time)"
    "$VENV_PY" - <<'PY'
import os
from huggingface_hub import hf_hub_download
d = os.path.expanduser('~/.cache/whisprlocal')
os.makedirs(d, exist_ok=True)
p = hf_hub_download('Qwen/Qwen2.5-1.5B-Instruct-GGUF',
                    'qwen2.5-1.5b-instruct-q4_k_m.gguf', local_dir=d)
print('  model at', p)
PY
fi

# --- 5. Starter config (don't clobber an existing one) ---------------------
CFG_DIR="$HOME/.config/whisprlocal"
CFG_PATH="$CFG_DIR/config.toml"
if [ ! -f "$CFG_PATH" ]; then
    echo "==> Writing starter config to $CFG_PATH"
    mkdir -p "$CFG_DIR"
    if [ "$WITH_LLM" = "1" ]; then
        sed 's/llm_cleanup = false/llm_cleanup = true/' config.example.toml > "$CFG_PATH"
    else
        cp config.example.toml "$CFG_PATH"
    fi
else
    echo "==> Keeping existing config at $CFG_PATH"
fi

echo ""
echo "Done. To run:"
echo "  ./.venv/bin/whisprlocal      # or: ./.venv/bin/python -m whisprlocal"
echo "Then hold Ctrl+Alt, speak, release."
