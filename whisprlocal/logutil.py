"""Central logging: writes to a rotating file on the user's machine + console.

The daemon usually runs windowless (pythonw), so console output is lost. This
routes everything to a log file so you can see what was transcribed, what the
cleanup produced, and how text was injected.

Log location:
  Windows: %LOCALAPPDATA%\\whisprlocal\\logs\\whisprlocal.log
  macOS:   ~/Library/Logs/whisprlocal/whisprlocal.log
  Linux:   ${XDG_STATE_HOME:-~/.local/state}/whisprlocal/whisprlocal.log
"""
from __future__ import annotations

import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

_LOGGER_NAME = "whisprlocal"
_configured = False


def log_dir() -> Path:
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Logs"
    else:
        base = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local" / "state"))
    d = (base / "whisprlocal" / "logs") if sys.platform == "win32" else (base / "whisprlocal")
    d.mkdir(parents=True, exist_ok=True)
    return d


def log_path() -> Path:
    return log_dir() / "whisprlocal.log"


def setup_logging(level: int = logging.INFO) -> logging.Logger:
    """Configure the shared logger once. Safe to call multiple times."""
    global _configured
    logger = logging.getLogger(_LOGGER_NAME)
    if _configured:
        return logger
    logger.setLevel(level)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s", "%Y-%m-%d %H:%M:%S")

    # Rotating file (1 MB x 3 backups) on the user's machine.
    try:
        fh = RotatingFileHandler(
            log_path(), maxBytes=1_000_000, backupCount=3, encoding="utf-8"
        )
        fh.setFormatter(fmt)
        logger.addHandler(fh)
    except Exception as e:  # never let logging break the app
        print(f"[log] could not open log file: {e}", file=sys.stderr)

    # Console too (visible when run from a terminal).
    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    logger.addHandler(sh)

    _configured = True
    logger.info("logging to %s", log_path())
    return logger


def get_logger() -> logging.Logger:
    return logging.getLogger(_LOGGER_NAME)
