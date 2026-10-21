"""User settings, loaded from ~/.yapper/config.json (env vars / CLI flags win for a run)."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

CONFIG_PATH = Path.home() / ".yapper" / "config.json"
VERSION = 2

MODELS = ("base", "tiny")
PRECISIONS = ("int8", "fp32")
DEVICES = ("auto", "cuda", "cpu")


@dataclass
class Config:
    version: int = VERSION
    model: str = "base"        # base (most accurate, downloaded once) | tiny (fastest, bundled)
    precision: str = "int8"    # int8 (small + fast) | fp32 (full precision, larger download)
    device: str = "auto"       # auto (GPU if available) | cuda | cpu
    beam_size: int = 1
    cpu_threads: int = 0       # 0 = auto
    sample_rate: int = 16000

    hotkey: str = "ctrl_r"     # push-to-talk key (pynput name)
    min_seconds: float = 0.35  # ignore taps shorter than this
    postroll_s: float = 0.4    # keep capturing this long after key release (early-release tail)
    silence_peak: float = 0.02 # ignore captures quieter than this (no speech)

    auto_paste: bool = True
    trailing_space: bool = True
    restore_clipboard: bool = True

    mascot: bool = True
    size: str = "small"        # small | medium | large
    pos: list | None = None    # saved mascot corner after dragging
    done_hold_ms: int = 1000

    @classmethod
    def load(cls) -> "Config":
        cfg = cls()
        if CONFIG_PATH.exists():
            try:
                data = json.loads(CONFIG_PATH.read_text("utf-8"))
                if data.get("version", 1) < VERSION:      # v1 file: its model/device no longer apply
                    for k in ("model", "device", "version"):
                        data.pop(k, None)
                for k, v in data.items():
                    if hasattr(cfg, k):
                        setattr(cfg, k, v)
            except Exception as e:
                print(f"[config] ignoring bad {CONFIG_PATH}: {e}")
        cfg.model = os.environ.get("YAPPER_MODEL", cfg.model)
        cfg.precision = os.environ.get("YAPPER_PRECISION", cfg.precision)
        cfg.device = os.environ.get("YAPPER_DEVICE", cfg.device)
        for name, allowed, default in (("model", MODELS, "base"), ("precision", PRECISIONS, "int8"),
                                       ("device", DEVICES, "auto")):
            if getattr(cfg, name) not in allowed:
                print(f"[config] unknown {name} {getattr(cfg, name)!r}; using {default!r}")
                setattr(cfg, name, default)
        return cfg

    def save(self, *keys: str) -> None:
        """Persist only the given settings (so one-off CLI flags never get saved)."""
        data = {}
        if CONFIG_PATH.exists():
            try:
                data = json.loads(CONFIG_PATH.read_text("utf-8"))
            except Exception:
                data = {}
        if data.get("version", 1) < VERSION:
            data = {k: v for k, v in data.items() if k not in ("model", "device")}
        data.update({k: getattr(self, k) for k in keys}, version=VERSION)
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        CONFIG_PATH.write_text(json.dumps(data, indent=2), "utf-8")
