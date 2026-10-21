"""Push-to-talk pipeline: hotkey -> record -> transcribe (worker) -> paste.

Pressing the hotkey again mid-transcription starts a new clip and drops the old
one (a session id invalidates stale work). Inference is serialised by a lock.
"""
from __future__ import annotations

import threading

import numpy as np
from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QGuiApplication

from .paste import send_ctrl_v
from .recorder import Recorder


class Controller(QObject):
    sig_state = Signal(str)     # loading/idle/listening/processing/done/error
    sig_paste = Signal(str)
    sig_ready = Signal(bool)

    def __init__(self, config, asr):
        super().__init__()
        self.cfg = config
        self.asr = asr
        self.recorder = Recorder(config.sample_rate)
        self.ready = False
        self._session = 0
        self._lock = threading.Lock()
        self.sig_paste.connect(self._do_paste)

    def load_models(self) -> None:
        def _run():
            try:
                self.asr.load()
                self.recorder.ensure_open()
                self.ready = True
                self.sig_ready.emit(True)
            except Exception as e:
                print(f"[yapper] model load failed: {e}")
                self.sig_ready.emit(False)
        threading.Thread(target=_run, daemon=True).start()

    def on_hotkey_start(self) -> None:
        if not self.ready or self.recorder.recording:
            return
        self._session += 1
        self.recorder.start()
        self.sig_state.emit("listening")

    def on_hotkey_stop(self) -> None:
        if not self.recorder.recording:
            return
        # keep capturing a short tail: users often release the key before they
        # finish the last word. The stream is always live, so just delay stop().
        threading.Timer(self.cfg.postroll_s, self._finalize).start()

    def _finalize(self) -> None:
        if not self.recorder.recording:
            return
        audio = self.recorder.stop()
        session = self._session
        too_short = audio.size < self.cfg.min_seconds * self.cfg.sample_rate
        silent = audio.size == 0 or float(np.abs(audio).max()) < self.cfg.silence_peak
        if too_short or silent:
            if session == self._session:
                self.sig_state.emit("idle")
            return
        self.sig_state.emit("processing")
        threading.Thread(target=self._process, args=(audio, session), daemon=True).start()

    def _process(self, audio, session: int) -> None:
        with self._lock:
            if session != self._session:
                return
            try:
                text = self.asr.transcribe(audio)
                if session != self._session:
                    return
                if not text:
                    self.sig_state.emit("idle")
                    return
                if self.cfg.trailing_space:
                    text = text.rstrip() + " "
                self.sig_paste.emit(text)
                self.sig_state.emit("done")
            except Exception as e:
                print(f"[yapper] transcription error: {e}")
                if session == self._session:
                    self.sig_state.emit("error")

    def _do_paste(self, text: str) -> None:
        clip = QGuiApplication.clipboard()
        prev = clip.text() if self.cfg.restore_clipboard else None
        clip.setText(text)
        if self.cfg.auto_paste:
            send_ctrl_v()
            if self.cfg.restore_clipboard and prev is not None:
                from PySide6.QtCore import QTimer
                QTimer.singleShot(400, lambda: clip.setText(prev))
