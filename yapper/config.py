"""Yapper configuration. Override any field via ~/.yapper/config.json."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

CONFIG_PATH = Path.home() / ".yapper" / "config.json"

# Hugging Face model id — a CTranslate2 export of the romanized Whisper-tiny.
# Set this to your published model, or point `model_dir` at a local CTranslate2 folder.
DEFAULT_MODEL_ID = "abhishekgautamm/whisper-tiny-hinglish-ct2"


@dataclass
class Config:
    # push-to-talk key (pynput Key name). Right Ctrl avoids clobbering Ctrl+C/V shortcuts.
    hotkey: str = "ctrl_r"

    # model (CTranslate2 / faster-whisper)
    # By default Yapper uses the int8 model bundled in the repo (fast, small, fully offline).
    # For better accuracy, set download_from_hf: true and compute_type: "float32" — Yapper then
    # downloads the full-precision model from `model_id` on first run (cached).
    download_from_hf: bool = False     # False = bundled int8 model | True = download model_id
    model_id: str = DEFAULT_MODEL_ID   # HF repo (CTranslate2 float32) for the accurate model
    model_dir: str = ""                # optional: a specific local CTranslate2 folder (has model.bin)
    compute_type: str = "int8"         # int8 (smallest/fastest) | int8_float32 | float32 (accurate)
    language: str = "en"               # decoder language token ("" = autodetect)
    beam_size: int = 1                 # 1 = greedy (fastest); raise to 5 for slightly better output
    cpu_threads: int = 0               # 0 = auto
    sample_rate: int = 16000

    # behaviour
    min_seconds: float = 0.4           # ignore accidental taps shorter than this
    auto_paste: bool = True            # paste into the focused field (else just copy)
    trailing_space: bool = True        # append a space so back-to-back dictation stays separated
    restore_clipboard: bool = True     # put the previous clipboard back after pasting

    # mascot / UI
    mascot: bool = True                # show the animated mascot (False = tray only)
    size: str = "small"                # mascot size: small | medium | large
    pos: list | None = None            # saved mascot top-left [x, y] after dragging (None = corner)
    done_hold_ms: int = 1000           # how long the "done" state shows before idling

    @classmethod
    def load(cls) -> "Config":
        cfg = cls()
        if CONFIG_PATH.exists():
            try:
                for k, v in json.loads(CONFIG_PATH.read_text(encoding="utf-8")).items():
                    if hasattr(cfg, k):
                        setattr(cfg, k, v)
            except Exception as e:
                print(f"[config] ignoring bad {CONFIG_PATH}: {e}")
        return cfg

    def save(self) -> None:
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        CONFIG_PATH.write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")
