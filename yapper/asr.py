"""Speech-to-text: fine-tuned Whisper (tiny or base) on faster-whisper / CTranslate2.
Output is romanized Hindi / English / Hinglish.

Device: "auto" uses an NVIDIA GPU when one is usable, else CPU.
Precision: "int8" (default, small + fast) or "fp32" (full precision).
"""
from __future__ import annotations

import glob
import os
import sys

import numpy as np

from . import models

_COMPUTE = {("int8", "cuda"): "int8_float16", ("int8", "cpu"): "int8",
            ("fp32", "cuda"): "float32", ("fp32", "cpu"): "float32"}


def cuda_dirs() -> list:
    """Folders that may hold the CUDA 12 / cuDNN 9 runtime: Yapper's own pip copy first,
    then a system-wide CUDA Toolkit / cuDNN install."""
    dirs = []
    for sp in sys.path:                                         # pip: nvidia-cublas-cu12, ...
        dirs += glob.glob(os.path.join(sp, "nvidia", "*", "bin" if os.name == "nt" else "lib"))
    if os.name == "nt":
        pf = os.environ.get("ProgramFiles", r"C:\Program Files")
        roots = [v for k, v in os.environ.items() if k.upper().startswith("CUDA_PATH")]
        roots += glob.glob(os.path.join(pf, "NVIDIA GPU Computing Toolkit", "CUDA", "v12*"))
        dirs += [os.path.join(r, "bin") for r in roots]
        dirs += glob.glob(os.path.join(pf, "NVIDIA", "CUDNN", "v9*", "bin", "12*"))
        dirs += glob.glob(os.path.join(pf, "NVIDIA", "CUDNN", "v9*", "bin"))
    else:
        dirs += glob.glob("/usr/local/cuda*/lib64")
    return [d for d in dict.fromkeys(dirs) if os.path.isdir(d)]


def _add_cuda_dlls() -> None:
    """Windows: make the CUDA libraries findable (Linux uses LD_LIBRARY_PATH, set by run.py)."""
    if os.name != "nt":
        return
    for d in cuda_dirs():
        try:
            os.add_dll_directory(d)
        except OSError:
            pass
        if d not in os.environ.get("PATH", ""):
            os.environ["PATH"] = os.environ.get("PATH", "") + os.pathsep + d


def cuda_available() -> bool:
    _add_cuda_dlls()
    try:
        import ctranslate2
        return ctranslate2.get_cuda_device_count() > 0
    except Exception:
        return False


def gpu_works() -> bool:
    """True if Whisper actually runs on the GPU with the CUDA libraries available right now."""
    _add_cuda_dlls()
    try:
        from faster_whisper import WhisperModel
        m = WhisperModel(str(models.BUNDLED), device="cuda", compute_type="int8_float16")
        list(m.transcribe(np.zeros(16000, np.float32), language="en", beam_size=1, without_timestamps=True)[0])
        return True
    except Exception:
        return False


def _lead_pad(audio: np.ndarray, sr: int, seconds: float = 0.4) -> np.ndarray:
    # a little leading silence stops the decoder mangling the first word
    n = int(sr * seconds)
    a = audio.astype(np.float32)
    return np.concatenate([np.zeros(n, np.float32), a]) if n else a


def _normalize(audio: np.ndarray, target_rms: float = 0.08,
               floor: float = 1e-4, max_gain: float = 20.0) -> np.ndarray:
    """Loudness-normalize so quiet / far-away speech reaches the level Whisper
    expects (quiet input -> low-energy mels -> hallucination). RMS-based with a
    gain cap (so we don't blow up pure noise) and peak safety (no clipping)."""
    if audio.size == 0:
        return audio
    rms = float(np.sqrt(np.mean(audio.astype(np.float64) ** 2)))
    if rms < floor:                       # essentially silence -> leave as-is
        return audio.astype(np.float32)
    a = audio * min(target_rms / rms, max_gain)
    peak = float(np.abs(a).max())
    if peak > 0.99:
        a = a * (0.99 / peak)
    return a.astype(np.float32)


class ASR:
    def __init__(self, cfg):
        self.cfg = cfg
        self._m = None
        self.source = f"{cfg.model} ({cfg.precision})"
        self.device = "cpu"

    # -- loading ------------------------------------------------------------
    def _path(self):
        try:
            return self.cfg.model, self.cfg.precision, models.resolve(self.cfg.model, self.cfg.precision)
        except Exception as e:
            if (self.cfg.model, self.cfg.precision) == ("tiny", "int8"):
                raise
            reason = (str(e).strip().splitlines() or [type(e).__name__])[0]
            print(f"[yapper] could not download the {self.cfg.model} model ({reason}); "
                  f"using the bundled tiny model for now.", flush=True)
            return "tiny", "int8", models.resolve("tiny", "int8")

    def _open(self, path, precision, device):
        from faster_whisper import WhisperModel
        m = WhisperModel(str(path), device=device, compute_type=_COMPUTE[(precision, device)],
                         cpu_threads=self.cfg.cpu_threads or 0)
        list(m.transcribe(np.zeros(16000, np.float32), language="en", beam_size=1, without_timestamps=True)[0])  # warm-up: surfaces missing CUDA libs now
        return m

    def load(self):
        if self._m is not None:
            return self
        model, precision, path = self._path()
        _add_cuda_dlls()
        want_gpu = self.cfg.device == "cuda" or (self.cfg.device == "auto" and cuda_available())
        if want_gpu:
            try:
                self._m, self.device = self._open(path, precision, "cuda"), "cuda"
            except Exception as e:
                print(f"[yapper] GPU unavailable ({str(e).splitlines()[0]}); using CPU. "
                      f"To re-run the GPU setup, delete .venv/.installed and start Yapper again.")
        if self._m is None:
            self._m, self.device = self._open(path, precision, "cpu"), "cpu"
        self.source = f"{model} ({precision})"
        return self

    # -- inference ----------------------------------------------------------
    def transcribe(self, audio: np.ndarray) -> str:
        if audio is None or audio.size == 0:
            return ""
        self.load()
        segs, _ = self._m.transcribe(
            _lead_pad(_normalize(audio), self.cfg.sample_rate), language="en",
            beam_size=self.cfg.beam_size, temperature=0,
            condition_on_previous_text=False, vad_filter=False,
            without_timestamps=True,                          # the models were fine-tuned without timestamps
            no_repeat_ngram_size=3, repetition_penalty=1.1)   # anti-hallucination (matches the benchmark)
        return "".join(s.text for s in segs).strip()


def build(cfg) -> ASR:
    return ASR(cfg)
