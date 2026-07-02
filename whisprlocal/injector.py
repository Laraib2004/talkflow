"""Inject transcribed text into whatever app currently has focus.

Uses pynput's keyboard controller to "type" the string, which works in
essentially any text field on macOS, Windows, and Linux (X11).
For long strings, clipboard-paste is faster and avoids per-keystroke lag.
"""
from __future__ import annotations

import sys
import time

from pynput.keyboard import Controller, Key

from .logutil import get_logger

log = get_logger()
_kbd = Controller()

# Threshold above which we paste via clipboard instead of typing char-by-char
_PASTE_THRESHOLD = 60

# Clipboard-paste timing. Pasting is asynchronous: the target app reads the
# clipboard some time *after* we send Ctrl+V. If we restore the previous
# clipboard too soon, the app pastes the OLD contents instead — this is the
# "it pasted my clipboard" bug. So we (a) confirm our text actually landed on
# the clipboard before pasting, and (b) wait for the app to consume it before
# restoring.
_CLIP_SET_TIMEOUT = 0.6     # max wait for our copy to appear on the clipboard
_CLIP_CONSUME_WAIT = 0.18   # wait after Ctrl+V before restoring the old clipboard


def type_text(text: str):
    if not text:
        return
    if len(text) > _PASTE_THRESHOLD and _paste_via_clipboard(text):
        log.info("injected via paste (%d chars)", len(text))
        return
    _kbd.type(text)
    log.info("injected via typing (%d chars)", len(text))


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
    log.info("placeholder shown (%d chars): %r", len(text), text)
    return len(text)


def delete_chars(n: int):
    """Erase the last *n* typed characters with backspaces (removes a placeholder)."""
    for _ in range(max(0, n)):
        _kbd.press(Key.backspace)
        _kbd.release(Key.backspace)
    if n:
        log.info("placeholder removed (%d backspaces)", n)


def _set_clipboard(pyperclip, text: str) -> bool:
    """Copy *text* and confirm it actually landed before we rely on it."""
    pyperclip.copy(text)
    deadline = time.time() + _CLIP_SET_TIMEOUT
    while time.time() < deadline:
        try:
            if pyperclip.paste() == text:
                return True
        except Exception:
            pass
        time.sleep(0.01)
    return False


def _paste_via_clipboard(text: str) -> bool:
    try:
        import pyperclip
    except ImportError:
        log.warning("pyperclip missing; cannot paste, will type instead")
        return False

    prev = None
    try:
        prev = pyperclip.paste()
    except Exception:
        pass

    # Confirm our text is on the clipboard BEFORE pasting, so we never paste
    # stale contents because the copy hadn't taken effect yet.
    if not _set_clipboard(pyperclip, text):
        log.warning("clipboard did not accept our text; falling back to typing")
        return False

    mod = Key.cmd if sys.platform == "darwin" else Key.ctrl
    with _kbd.pressed(mod):
        _kbd.press("v")
        _kbd.release("v")

    # Let the target app actually read the clipboard before we restore, or it
    # will paste the OLD clipboard instead of our text.
    time.sleep(_CLIP_CONSUME_WAIT)

    if prev is not None and prev != text:
        try:
            pyperclip.copy(prev)  # restore user's clipboard
            log.debug("clipboard restored (%d chars)", len(prev))
        except Exception:
            pass
    return True
