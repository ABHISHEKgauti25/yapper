"""
Speech-to-text: romanized Hindi/English/Hinglish Whisper-tiny on CTranslate2 (via faster-whisper).

CPU-only, and at runtime it needs no PyTorch / Transformers — just faster-whisper's small
CTranslate2 engine. The model is a CTranslate2 export of the fine-tuned Whisper-tiny:
  - use a local folder (config `model_dir`, or a `models/<name>/` folder next to the repo), or
  - download it from Hugging Face on first run (config `model_id`).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

# a model bundled/placed next to the repo (models/<name>/ with a model.bin) is used if present
_BUNDLED = Path(__file__).resolve().parent.parent / "models"


def _resolve_model(cfg) -> str:
    # 1) explicit local folder always wins
    if cfg.model_dir and (Path(cfg.model_dir) / "model.bin").exists():
        return cfg.model_dir
    # 2) opt-in: the full-precision model from Hugging Face (better accuracy)
    if getattr(cfg, "download_from_hf", False):
        return cfg.model_id
    # 3) default: the int8 model bundled in the repo (offline, small, fast)
    if _BUNDLED.is_dir():
        for p in sorted(_BUNDLED.iterdir()):
            if p.is_dir() and (p / "model.bin").exists():
                return str(p)
    # 4) fallback: Hugging Face
    return cfg.model_id


class WhisperASR:
    def __init__(self, cfg):
        self.cfg = cfg
        self._model = None
        self.source = ""

    def load(self) -> "WhisperASR":
        if self._model is not None:
            return self
        from faster_whisper import WhisperModel
        src = _resolve_model(self.cfg)
        self._model = WhisperModel(
            src, device="cpu",
            compute_type=self.cfg.compute_type,
            cpu_threads=(self.cfg.cpu_threads or 0),
        )
        self.source = src
        return self

    def transcribe(self, audio: np.ndarray) -> str:
        if audio is None or audio.size == 0:
            return ""
        self.load()
        segments, _ = self._model.transcribe(
            audio.astype(np.float32),
            language=(self.cfg.language or None),
            beam_size=self.cfg.beam_size,
            vad_filter=False,
        )
        return "".join(s.text for s in segments).strip()
