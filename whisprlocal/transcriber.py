"""Local speech-to-text via faster-whisper (CTranslate2 backend)."""
from __future__ import annotations

import glob
import os
import site

import numpy as np
from faster_whisper import WhisperModel

from .logutil import get_logger

log = get_logger()


def _enable_cuda_libs() -> None:
    """Make pip-installed NVIDIA CUDA libs (cublas/cudnn/...) loadable.

    When installed via wheels (nvidia-cublas-cu12, nvidia-cudnn-cu12, ...), the
    DLLs live under site-packages/nvidia/*/bin. CTranslate2 resolves them via
    PATH, so we prepend those dirs. No-op if the packages aren't installed.
    """
    try:
        roots = site.getsitepackages() + [site.getusersitepackages()]
    except Exception:  # some envs lack getusersitepackages
        roots = site.getsitepackages()
    bins = [
        d for base in roots
        for d in glob.glob(os.path.join(base, "nvidia", "*", "bin"))
    ]
    if not bins:
        return
    os.environ["PATH"] = os.pathsep.join(bins) + os.pathsep + os.environ.get("PATH", "")
    for d in bins:
        try:
            os.add_dll_directory(d)
        except (OSError, AttributeError):
            pass


class Transcriber:
    def __init__(
        self,
        model: str = "base.en",
        device: str = "cpu",
        compute_type: str = "int8",
        language: str | None = "en",
        beam_size: int = 1,
    ):
        self.language = language
        self.beam_size = beam_size
        if device.startswith("cuda"):
            _enable_cuda_libs()
        # download_root defaults to ~/.cache/huggingface; model is cached after first run
        try:
            self.model = WhisperModel(model, device=device, compute_type=compute_type)
        except Exception as e:  # noqa: BLE001 — degrade instead of crashing the daemon
            if device.startswith("cuda"):
                log.warning("CUDA unavailable (%s); falling back to CPU int8.", e)
                self.model = WhisperModel(model, device="cpu", compute_type="int8")
            else:
                raise

    def transcribe(self, audio: np.ndarray, samplerate: int) -> str:
        # faster-whisper expects mono float32 @ 16 kHz
        if samplerate != 16000:
            audio = _resample(audio, samplerate, 16000)
        segments, _ = self.model.transcribe(
            audio,
            language=self.language,
            beam_size=self.beam_size,  # 1 = greedy, fastest; higher = slower/more accurate
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
