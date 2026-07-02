"""Inject transcribed text into whatever app currently has focus.

Uses pynput's keyboard controller to "type" the string, which works in
essentially any text field on macOS, Windows, and Linux (X11).
For long strings, clipboard-paste is faster and avoids per-keystroke lag.
"""
from __future__ import annotations

import time
from pynput.keyboard import Controller, Key

_kbd = Controller()

# Threshold above which we paste via clipboard instead of typing char-by-char
_PASTE_THRESHOLD = 60


def type_text(text: str):
    if not text:
        return
    if len(text) > _PASTE_THRESHOLD and _paste_via_clipboard(text):
        return
    _kbd.type(text)


def type_placeholder(text: str) -> int:
    """Insert a transient placeholder, returning how many chars to delete later.

    Pastes rather than types: bracket/paren auto-pairing in code editors would
    otherwise insert extra characters and desync the delete count. Falls back to
    typing if the clipboard path is unavailable.
    """
    if not text:
        return 0
    if not _paste_via_clipboard(text):
        _kbd.type(text)
    return len(text)


def delete_chars(n: int):
    """Erase the last *n* typed characters with backspaces (removes a placeholder)."""
    for _ in range(max(0, n)):
        _kbd.press(Key.backspace)
        _kbd.release(Key.backspace)


def _paste_via_clipboard(text: str) -> bool:
    try:
        import pyperclip
    except ImportError:
        return False
    import sys

    prev = None
    try:
        prev = pyperclip.paste()
    except Exception:
        pass
    pyperclip.copy(text)
    time.sleep(0.03)

    mod = Key.cmd if sys.platform == "darwin" else Key.ctrl
    with _kbd.pressed(mod):
        _kbd.press("v")
        _kbd.release("v")
    time.sleep(0.05)

    if prev is not None:
        try:
            pyperclip.copy(prev)  # restore user's clipboard
        except Exception:
            pass
    return True
