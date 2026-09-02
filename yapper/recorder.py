"""
Push-to-talk audio capture via sounddevice.

The input stream is kept OPEN continuously and we just flip a `capturing` flag on hotkey —
so start/stop are instant (no per-press device-open latency). A short rolling pre-roll buffer
is prepended on start so the first syllable isn't clipped.
"""
from __future__ import annotations

import threading
from collections import deque

import numpy as np
import sounddevice as sd


class Recorder:
    def __init__(self, sample_rate: int = 16000, preroll_s: float = 0.25):
        self.sample_rate = sample_rate
        self._block = 1600  # 100 ms blocks
        self._preroll = deque(maxlen=max(1, round(preroll_s * sample_rate / self._block)))
        self._capturing = False
        self._chunks: list[np.ndarray] = []
        self._lock = threading.Lock()
        self._stream: sd.InputStream | None = None

    def ensure_open(self) -> None:
        """Open + start the persistent stream (call once after models load to warm the mic)."""
        if self._stream is not None:
            return
        stream = sd.InputStream(
            samplerate=self.sample_rate, channels=1, dtype="float32",
            blocksize=self._block, callback=self._callback,
        )
        stream.start()
        self._stream = stream

    def _callback(self, indata, frames, time_info, status):  # PortAudio thread
        block = indata.copy().reshape(-1)
        with self._lock:
            if self._capturing:
                self._chunks.append(block)
            else:
                self._preroll.append(block)

    def start(self) -> None:
        self.ensure_open()
        with self._lock:
            self._chunks = list(self._preroll)   # seed with the pre-roll so onset isn't lost
            self._capturing = True

    def stop(self) -> np.ndarray:
        with self._lock:
            self._capturing = False
            chunks, self._chunks = self._chunks, []
        if not chunks:
            return np.zeros(0, dtype=np.float32)
        return np.concatenate(chunks).astype(np.float32)

    @property
    def recording(self) -> bool:
        return self._capturing

    def close(self) -> None:
        if self._stream is not None:
            try:
                self._stream.stop(); self._stream.close()
            finally:
                self._stream = None
