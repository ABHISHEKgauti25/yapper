"""
Pipeline: hotkey -> record -> (worker thread) transcribe -> paste.

State machine, driven by push-to-talk:
    idle --press--> listening --release--> processing --> done --> idle

Barge-in: pressing the hotkey again while a clip is still being transcribed starts a new
recording immediately and drops the previous result (a session id invalidates stale work).
Transcription is serialised by a lock so two clips never decode at once.

There is intentionally NO language-model cleanup step — Yapper outputs the raw romanized
transcription. (Optional post-transcription correction is on the roadmap; see the README.)
"""
from __future__ import annotations

import threading

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QGuiApplication

from .paste import send_ctrl_v
from .recorder import Recorder


class Controller(QObject):
    sig_state = Signal(str)     # loading/idle/listening/processing/done/error
    sig_paste = Signal(str)     # text to place on clipboard + paste (main thread)
    sig_ready = Signal(bool)    # model finished loading (True) or failed (False)

    def __init__(self, config, asr):
        super().__init__()
        self.cfg = config
        self.asr = asr
        self.recorder = Recorder(config.sample_rate)
        self.ready = False
        self._session = 0
        self._infer_lock = threading.Lock()
        self.sig_paste.connect(self._do_paste)

    # ---- model loading (background thread) ----
    def load_models(self) -> None:
        def _run():
            try:
                self.asr.load()
                self.recorder.ensure_open()   # warm the mic so the first press is instant
                self.ready = True
                self.sig_ready.emit(True)
            except Exception as e:  # noqa: BLE001
                print(f"[controller] model load failed: {e}")
                self.sig_ready.emit(False)
        threading.Thread(target=_run, daemon=True).start()

    # ---- hotkey callbacks (pynput thread) ----
    def on_hotkey_start(self) -> None:
        if not self.ready or self.recorder.recording:
            return
        self._session += 1
        self.recorder.start()
        self.sig_state.emit("listening")

    def on_hotkey_stop(self) -> None:
        if not self.recorder.recording:
            return
        audio = self.recorder.stop()
        session = self._session
        if audio.size < self.cfg.min_seconds * self.cfg.sample_rate:
            if session == self._session:
                self.sig_state.emit("idle")
            return
        self.sig_state.emit("processing")
        threading.Thread(target=self._process, args=(audio, session), daemon=True).start()

    # ---- worker thread ----
    def _stale(self, session: int) -> bool:
        return session != self._session

    def _process(self, audio, session: int) -> None:
        with self._infer_lock:
            if self._stale(session):
                return
            try:
                text = self.asr.transcribe(audio)
                if self._stale(session):
                    return
                if not text.strip():
                    self.sig_state.emit("idle")
                    return
                if self.cfg.trailing_space:
                    text = text.rstrip() + " "
                self.sig_paste.emit(text)
                self.sig_state.emit("done")
            except Exception as e:  # noqa: BLE001
                print(f"[controller] transcription error: {e}")
                if not self._stale(session):
                    self.sig_state.emit("error")

    # ---- main-thread paste ----
    def _do_paste(self, text: str) -> None:
        clip = QGuiApplication.clipboard()
        prev = clip.text() if self.cfg.restore_clipboard else None
        clip.setText(text)
        if self.cfg.auto_paste:
            send_ctrl_v()
            if self.cfg.restore_clipboard and prev is not None:
                from PySide6.QtCore import QTimer
                QTimer.singleShot(400, lambda: clip.setText(prev))
