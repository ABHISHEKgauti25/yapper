"""Mic capture. The stream stays open; a hotkey just flips `capturing`, so
start/stop are instant. A short pre-roll is kept so the first syllable survives."""
from __future__ import annotations

import threading
from collections import deque

import numpy as np
import sounddevice as sd


class Recorder:
    def __init__(self, sample_rate: int = 16000, preroll_s: float = 0.6):
        self.sample_rate = sample_rate
        self._block = 1600  # 100 ms
        self._preroll = deque(maxlen=max(1, round(preroll_s * sample_rate / self._block)))
        self._capturing = False
        self._chunks: list[np.ndarray] = []
        self._lock = threading.Lock()
        self._stream: sd.InputStream | None = None

    def ensure_open(self) -> None:
        if self._stream is not None:
            return
        self._stream = sd.InputStream(samplerate=self.sample_rate, channels=1, dtype="float32",
                                      blocksize=self._block, callback=self._callback)
        self._stream.start()

    def _callback(self, indata, frames, time_info, status):
        block = indata.copy().reshape(-1)
        with self._lock:
            (self._chunks if self._capturing else self._preroll).append(block)

    def start(self) -> None:
        self.ensure_open()
        with self._lock:
            self._chunks = list(self._preroll)
            self._capturing = True

    def stop(self) -> np.ndarray:
        with self._lock:
            self._capturing = False
            chunks, self._chunks = self._chunks, []
        return np.concatenate(chunks).astype(np.float32) if chunks else np.zeros(0, np.float32)

    @property
    def recording(self) -> bool:
        return self._capturing

    def close(self) -> None:
        if self._stream is not None:
            try:
                self._stream.stop(); self._stream.close()
            finally:
                self._stream = None
