"""Transcribe audio files from the command line (no GUI):  python run.py --transcribe a.wav b.mp3"""
from __future__ import annotations

import sys
import time

from faster_whisper import decode_audio

from yapper import asr
from yapper.config import Config


def main(paths: list[str]) -> None:
    cfg = Config.load()
    t = time.time()
    m = asr.build(cfg).load()
    print(f"[yapper] {m.source} on {m.device} | loaded in {time.time() - t:.1f}s", file=sys.stderr, flush=True)
    for p in paths:
        audio = decode_audio(p, sampling_rate=cfg.sample_rate)
        t = time.time()
        text = m.transcribe(audio)
        print(f"[yapper] {p}  ({len(audio) / cfg.sample_rate:.1f}s audio, {time.time() - t:.2f}s)", file=sys.stderr, flush=True)
        print(text, flush=True)
