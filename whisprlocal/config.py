"""Configuration for WhisprLocal."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

try:
    import tomllib  # py3.11+
except ModuleNotFoundError:  # pragma: no cover
    tomllib = None

from pynput import keyboard

_CONFIG_PATH = Path(
    os.environ.get("WHISPRLOCAL_CONFIG", Path.home() / ".config" / "whisprlocal" / "config.toml")
)

# Map friendly names -> pynput keys for the hotkey combo
_KEYMAP = {
    "ctrl": keyboard.Key.ctrl,
    "alt": keyboard.Key.alt,
    "shift": keyboard.Key.shift,
    "cmd": keyboard.Key.cmd,
    "super": keyboard.Key.cmd,
    "win": keyboard.Key.cmd,
    "space": keyboard.Key.space,
    "f9": keyboard.Key.f9,
    "f10": keyboard.Key.f10,
}


@dataclass
class Config:
    # Model: tiny.en / base.en / small.en / medium.en / large-v3
    model: str = "base.en"
    device: str = "cpu"          # "cpu" or "cuda"
    compute_type: str = "int8"   # int8 (cpu), float16 (gpu)
    language: str | None = "en"  # None = auto-detect
    samplerate: int = 16000
    hotkey: str = "ctrl+alt"     # hold-to-talk combo
    trailing_space: bool = True
    filler_level: int = 1        # 0=off, 1=um/uh, 2=also hedges (like, you know)

    # Semantic cleanup via a small local LLM (dedup sentences, false starts...).
    # Off by default; the regex pass above always runs regardless.
    llm_cleanup: bool = False
    # GGUF model file. ~/.cache path is the README's download target.
    llm_model_path: str = "~/.cache/whisprlocal/qwen2.5-1.5b-instruct-q4_k_m.gguf"
    # Seconds of no dictation before the model unloads itself (frees ~1 GB RAM).
    llm_idle_unload_seconds: float = 60.0
    # CPU threads for the LLM; None = llama.cpp default (physical cores).
    llm_threads: int | None = None

    def hotkey_set(self) -> set:
        keys = set()
        for part in self.hotkey.lower().split("+"):
            part = part.strip()
            if part in _KEYMAP:
                keys.add(_KEYMAP[part])
            elif len(part) == 1:
                keys.add(keyboard.KeyCode.from_char(part))
            else:
                raise ValueError(f"Unknown hotkey token: {part!r}")
        return keys

    @classmethod
    def load(cls) -> "Config":
        data: dict = {}
        if _CONFIG_PATH.exists() and tomllib:
            with open(_CONFIG_PATH, "rb") as f:
                data = tomllib.load(f)
        # env overrides
        env = {
            "model": os.environ.get("WHISPRLOCAL_MODEL"),
            "device": os.environ.get("WHISPRLOCAL_DEVICE"),
            "hotkey": os.environ.get("WHISPRLOCAL_HOTKEY"),
            "llm_model_path": os.environ.get("WHISPRLOCAL_LLM_MODEL_PATH"),
        }
        data.update({k: v for k, v in env.items() if v})
        # Boolean env toggle: WHISPRLOCAL_LLM=1 / true / yes
        _llm = os.environ.get("WHISPRLOCAL_LLM")
        if _llm is not None:
            data["llm_cleanup"] = _llm.strip().lower() in ("1", "true", "yes", "on")
        known = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in data.items() if k in known})
