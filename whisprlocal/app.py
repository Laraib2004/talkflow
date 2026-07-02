"""WhisprLocal — local, private voice dictation.

Hold a hotkey → speak → release → transcribed text is typed into the
focused app. Everything runs on-device via faster-whisper. No cloud.
"""
from __future__ import annotations

import sys
import time
import threading
import queue

import numpy as np
import sounddevice as sd
from pynput import keyboard

from .config import Config
from .transcriber import Transcriber
from .injector import type_text, type_placeholder, delete_chars
from .clean import clean_text
from .llm_clean import LLMCleaner


class Recorder:
    """Streams mic audio into a buffer while active."""

    def __init__(self, samplerate: int):
        self.samplerate = samplerate
        self._q: queue.Queue[np.ndarray] = queue.Queue()
        self._stream: sd.InputStream | None = None
        self._active = False

    def _callback(self, indata, frames, time_info, status):  # noqa: ANN001
        if status:
            print(f"[audio] {status}", file=sys.stderr)
        if self._active:
            self._q.put(indata.copy())

    def start(self):
        self._q = queue.Queue()
        self._active = True
        self._stream = sd.InputStream(
            samplerate=self.samplerate,
            channels=1,
            dtype="float32",
            callback=self._callback,
        )
        self._stream.start()

    def stop(self) -> np.ndarray:
        self._active = False
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        chunks = []
        while not self._q.empty():
            chunks.append(self._q.get())
        if not chunks:
            return np.zeros(0, dtype=np.float32)
        return np.concatenate(chunks, axis=0).flatten()


class WhisprLocal:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        print(f"[init] loading model '{cfg.model}' on {cfg.device} ...")
        self.transcriber = Transcriber(
            model=cfg.model,
            device=cfg.device,
            compute_type=cfg.compute_type,
            language=cfg.language,
            beam_size=cfg.beam_size,
        )
        self.recorder = Recorder(cfg.samplerate)
        # LLM cleaner is lazy: constructing it loads nothing. It only pulls the
        # model into RAM on hotkey-down and unloads after an idle timeout.
        self.llm = (
            LLMCleaner(
                model_path=cfg.llm_model_path,
                idle_unload_seconds=cfg.llm_idle_unload_seconds,
                n_threads=cfg.llm_threads,
            )
            if cfg.llm_cleanup
            else None
        )
        self._recording = False
        self._lock = threading.Lock()
        print("[init] ready. Hold the hotkey and speak.")

    # --- hotkey handling ---------------------------------------------------
    def _start(self):
        with self._lock:
            if self._recording:
                return
            self._recording = True
        print("[rec] listening...")
        # Start warming the LLM now so its load hides behind your speech +
        # transcription — no perceived lag when cleanup runs on release.
        if self.llm is not None:
            self.llm.warm()
        self.recorder.start()

    def _stop_and_transcribe(self):
        with self._lock:
            if not self._recording:
                return
            self._recording = False
        audio = self.recorder.stop()
        dur = len(audio) / self.cfg.samplerate
        if dur < 0.3:
            print("[rec] too short, ignored.")
            return
        print(f"[rec] {dur:.1f}s captured, transcribing...")
        t0 = time.time()
        text = self.transcriber.transcribe(audio, self.cfg.samplerate)
        text = clean_text(text, filler_level=self.cfg.filler_level)
        t_stt = time.time() - t0
        if self.llm is not None and self.llm.available and text:
            # Show a transient "thinking" placeholder in the focused field while
            # the LLM works, then delete it and type the cleaned result.
            n = type_placeholder(self.cfg.thinking_placeholder)
            text = self.llm.clean(text)
            delete_chars(n)
        print(f"[stt] (whisper {t_stt:.1f}s, total {time.time()-t0:.1f}s) -> {text!r}")
        if text:
            type_text(text + (" " if self.cfg.trailing_space else ""))

    def run(self):
        combo = self.cfg.hotkey_set()
        pressed: set = set()

        def normalize(key):
            # collapse left/right modifier variants
            return {
                keyboard.Key.ctrl_l: keyboard.Key.ctrl,
                keyboard.Key.ctrl_r: keyboard.Key.ctrl,
                keyboard.Key.alt_l: keyboard.Key.alt,
                keyboard.Key.alt_r: keyboard.Key.alt,
                keyboard.Key.shift_l: keyboard.Key.shift,
                keyboard.Key.shift_r: keyboard.Key.shift,
                keyboard.Key.cmd_l: keyboard.Key.cmd,
                keyboard.Key.cmd_r: keyboard.Key.cmd,
            }.get(key, key)

        def on_press(key):
            pressed.add(normalize(key))
            if combo.issubset(pressed):
                self._start()

        def on_release(key):
            n = normalize(key)
            if n in combo and self._recording:
                self._stop_and_transcribe()
            pressed.discard(n)

        with keyboard.Listener(on_press=on_press, on_release=on_release) as l:
            try:
                l.join()
            except KeyboardInterrupt:
                pass


def main():
    cfg = Config.load()
    WhisprLocal(cfg).run()


if __name__ == "__main__":
    main()
