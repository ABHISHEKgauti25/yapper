"""
Yapper — entry point.

Background voice dictation: hold the push-to-talk key (default Right Ctrl), speak, release,
and the romanized transcription is pasted into whatever field is focused. Lives in the system
tray; an optional animated mascot (bottom-right) shows the state.

Run:
    python -m yapper           (or: python run.py)
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from yapper.asr import WhisperASR  # noqa: E402

from PySide6.QtCore import Qt, QTimer  # noqa: E402
from PySide6.QtGui import QAction  # noqa: E402
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon  # noqa: E402

from yapper.config import Config  # noqa: E402
from yapper.controller import Controller  # noqa: E402
from yapper.hotkey import HotkeyListener  # noqa: E402
from yapper.mascot import mascot_icon  # noqa: E402

_SEEN = Path.home() / ".yapper" / ".seen"   # first-run marker


def _key_label(spec: str) -> str:
    if spec.startswith("ctrl"):
        return "Ctrl"
    if spec.startswith("alt"):
        return "Alt"
    if spec.startswith("cmd"):
        return "Cmd"
    return spec.upper()


def main() -> None:
    cfg = Config.load()

    # QtWebEngine (mascot renderer) wants a shared GL context set before the app is created.
    QApplication.setAttribute(Qt.AA_ShareOpenGLContexts, True)
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    # --- mascot (optional) ---
    mascot = None
    if cfg.mascot:
        from yapper.mascot import MascotWidget

        def _save_pos(x: int, y: int):
            cfg.pos = [x, y]
            cfg.save()

        mascot = MascotWidget(size=cfg.size, pos=cfg.pos, on_move=_save_pos)
        mascot.set_state("loading")
        mascot.show()

    asr = WhisperASR(cfg)
    controller = Controller(cfg, asr)
    hotkey = HotkeyListener(cfg.hotkey, controller.on_hotkey_start, controller.on_hotkey_stop)

    # --- tray ---
    tray = QSystemTrayIcon(mascot_icon(64))
    tray.setToolTip("Yapper — loading…")
    menu = QMenu()

    act_mascot = QAction("Show mascot", checkable=True)
    act_mascot.setChecked(cfg.mascot)
    menu.addAction(act_mascot)
    menu.addSeparator()
    act_quit = QAction("Quit Yapper")
    menu.addAction(act_quit)
    tray.setContextMenu(menu)
    tray.show()

    def toggle_mascot(on: bool):
        nonlocal mascot
        cfg.mascot = on
        cfg.save()
        if on and mascot is None:
            from yapper.mascot import MascotWidget
            def _save_pos(x, y): cfg.pos = [x, y]; cfg.save()
            mascot = MascotWidget(size=cfg.size, pos=cfg.pos, on_move=_save_pos)
            mascot.set_state("idle" if controller.ready else "loading")
            mascot.show()
        elif on and mascot is not None:
            mascot.show()
        elif not on and mascot is not None:
            mascot.hide()
        if not on:
            tray.showMessage("Yapper", "Mascot hidden — Yapper still runs in the tray.",
                             mascot_icon(64), 1500)
    act_mascot.toggled.connect(toggle_mascot)

    def quit_app():
        hotkey.stop()
        tray.hide()
        app.quit()
    act_quit.triggered.connect(quit_app)

    # --- state wiring (main thread) ---
    def on_state(state: str):
        if mascot is not None:
            mascot.set_state(state)
        if state == "done":
            QTimer.singleShot(cfg.done_hold_ms, lambda: on_state("idle"))
    controller.sig_state.connect(on_state)

    def on_ready(ok: bool):
        if ok:
            controller.ready = True
            on_state("idle")
            tray.setToolTip(f"Yapper — ready. Hold {cfg.hotkey} to talk.")
            hotkey.start()
            if mascot is not None and not _SEEN.exists():
                mascot.show_ready(f"Press {_key_label(cfg.hotkey)} to yap")
                try:
                    _SEEN.parent.mkdir(parents=True, exist_ok=True)
                    _SEEN.write_text("1", encoding="utf-8")
                except Exception:
                    pass
            print(f"[yapper] ready. hotkey={cfg.hotkey}  model={asr.source}")
        else:
            if mascot is not None:
                mascot.set_state("error")
            tray.setToolTip("Yapper — model load failed (see console).")
    controller.sig_ready.connect(on_ready)

    controller.load_models()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
