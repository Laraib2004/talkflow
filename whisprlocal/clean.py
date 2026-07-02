"""Light post-processing of raw transcripts.

Whisper transcribes speech faithfully, including filler words ("um", "uh",
"you know", "like"). This module removes them, handles spoken commands, and
tidies whitespace/casing.

Filler removal has two tiers:
  - ALWAYS: pure disfluencies that are never meaningful words (um, uh, er...).
    Removed at every aggressiveness level.
  - HEDGES: words that are usually filler but sometimes legitimate (like, so,
    actually, literally...). Only removed at aggressiveness >= 2, and only when
    they appear parenthetical (comma-flanked or at a clause edge) so we don't
    wreck "I'd like coffee" or "turn right".

Aggressiveness (config: filler_level):
  0 = off, keep everything
  1 = remove ALWAYS fillers only (default)
  2 = also remove HEDGES in clearly-parenthetical positions
"""
from __future__ import annotations

import re

_SPOKEN = {
    r"\bnew line\b": "\n",
    r"\bnew paragraph\b": "\n\n",
}

# Never-meaningful disfluencies. Also covers stutters like "um-um".
_ALWAYS = [
    "um", "uh", "erm", "er", "eh", "hmm", "mmm", "mm",
    "uhh", "umm", "ah", "huh",
]

# Usually filler, occasionally real. Removed only when parenthetical.
_HEDGES = [
    "you know", "i mean", "sort of", "kind of", "kinda", "sorta",
    "like", "basically", "actually", "literally", "honestly",
    "seriously", "right", "well", "so", "just",
]


def _build_always_re() -> re.Pattern:
    alt = "|".join(sorted(map(re.escape, _ALWAYS), key=len, reverse=True))
    # optional trailing comma so "um, hello" -> "hello"
    return re.compile(rf"\b(?:{alt})\b[ \t]*,?", re.IGNORECASE)


def _build_hedge_re() -> re.Pattern:
    alt = "|".join(sorted(map(re.escape, _HEDGES), key=len, reverse=True))
    # Only match when the hedge is set off by commas or sits at a clause
    # boundary: (start | comma) hedge (comma | end-of-clause punctuation).
    # This keeps "I'd like coffee" and "turn right" intact.
    return re.compile(
        rf"(^|(?<=[,]))\s*(?:{alt})\s*(?=[,.;!?]|$)",
        re.IGNORECASE,
    )


_ALWAYS_RE = _build_always_re()
_HEDGE_RE = _build_hedge_re()


def _remove_fillers(text: str, level: int) -> str:
    if level <= 0:
        return text
    text = _ALWAYS_RE.sub(" ", text)
    if level >= 2:
        prev = None
        while prev != text:  # repeat for back-to-back hedges
            prev = text
            text = _HEDGE_RE.sub(" ", text)
    return text


def _fix_orphan_punct(text: str) -> str:
    # After stripping words we can get " , " or ", ," or leading ", "
    text = re.sub(r",\s*(?=,)", "", text)            # collapse repeated commas
    text = re.sub(r"\s+([,.;!?])", r"\1", text)
    text = re.sub(r"([,;])\s*([,.;!?])", r"\2", text)
    text = re.sub(r"(^|[.!?]\s+),\s*", r"\1", text)
    return text


def _recapitalize(text: str) -> str:
    # Capitalize sentence starts (removal may have exposed a new one).
    def up(m):
        return m.group(1) + m.group(2).upper()
    text = re.sub(r"(^|[.!?]\s+)([a-z])", up, text)
    return text


def clean_text(text: str, filler_level: int = 1) -> str:
    if not text:
        return text
    for pat, repl in _SPOKEN.items():
        text = re.sub(pat, repl, text, flags=re.IGNORECASE)
    text = _remove_fillers(text, filler_level)
    text = _fix_orphan_punct(text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"[ \t]*\n[ \t]*", "\n", text)
    text = text.strip()
    text = _recapitalize(text)
    return text
