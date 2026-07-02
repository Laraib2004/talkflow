"""Local speech-to-text via faster-whisper (CTranslate2 backend)."""
from __future__ import annotations

import numpy as np
from faster_whisper import WhisperModel


class Transcriber:
    def __init__(
        self,
        model: str = "base.en",
        device: str = "cpu",
        compute_type: str = "int8",
        language: str | None = "en",
    ):
        self.language = language
        # download_root defaults to ~/.cache/huggingface; model is cached after first run
        self.model = WhisperModel(model, device=device, compute_type=compute_type)

    def transcribe(self, audio: np.ndarray, samplerate: int) -> str:
        # faster-whisper expects mono float32 @ 16 kHz
        if samplerate != 16000:
            audio = _resample(audio, samplerate, 16000)
        segments, _ = self.model.transcribe(
            audio,
            language=self.language,
            beam_size=5,
            vad_filter=True,  # drop leading/trailing silence
            condition_on_previous_text=False,
        )
        return "".join(seg.text for seg in segments).strip()


def _resample(audio: np.ndarray, src: int, dst: int) -> np.ndarray:
    if src == dst:
        return audio
    n = int(round(len(audio) * dst / src))
    x_old = np.linspace(0.0, 1.0, num=len(audio), endpoint=False)
    x_new = np.linspace(0.0, 1.0, num=n, endpoint=False)
    return np.interp(x_new, x_old, audio).astype(np.float32)
