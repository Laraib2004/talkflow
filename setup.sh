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
WORKDIR="$(pwd)"

WITH_LLM=1
AUTOSTART=0
for arg in "$@"; do
    case "$arg" in
        --no-llm)    WITH_LLM=0 ;;
        --autostart) AUTOSTART=1 ;;
    esac
done

echo "==> WhisprLocal setup (in $WORKDIR)"

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

# --- 6. Optional: install login autostart for this OS ----------------------
if [ "$AUTOSTART" = "1" ]; then
    VENV_PY="$WORKDIR/.venv/bin/python"
    VENV_BIN="$WORKDIR/.venv/bin/whisprlocal"
    case "$(uname -s)" in
        Darwin)
            PLIST="$HOME/Library/LaunchAgents/com.whisprlocal.agent.plist"
            echo "==> Installing macOS launchd agent -> $PLIST"
            mkdir -p "$HOME/Library/LaunchAgents"
            sed -e "s#__PYTHON__#$VENV_PY#g" -e "s#__WORKDIR__#$WORKDIR#g" \
                whisprlocal-autostart.plist > "$PLIST"
            launchctl unload "$PLIST" 2>/dev/null || true
            launchctl load "$PLIST"
            echo "    Loaded now, and will start at each login."
            ;;
        Linux)
            DESK="$HOME/.config/autostart/whisprlocal.desktop"
            echo "==> Installing Linux autostart entry -> $DESK"
            mkdir -p "$HOME/.config/autostart"
            sed -e "s#__EXEC__#$VENV_BIN#g" -e "s#__WORKDIR__#$WORKDIR#g" \
                whisprlocal.desktop > "$DESK"
            echo "    Installed. Starts at next login (X11 session)."
            ;;
        *)
            echo "==> --autostart: unsupported OS '$(uname -s)'. On Windows use setup.ps1 -Autostart."
            ;;
    esac
fi

echo ""
echo "Done. To run now:"
echo "  ./.venv/bin/whisprlocal      # or: ./.venv/bin/python -m whisprlocal"
echo "Then hold Ctrl+Alt, speak, release."
echo "(Re-run with --autostart to also launch it automatically on login.)"
