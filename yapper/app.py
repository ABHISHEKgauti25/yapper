"""Yapper — hold the hotkey (default Right Ctrl), speak, release; the romanized
text is pasted into the focused field. Lives in the tray with an optional mascot."""
from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from yapper import asr
from yapper.config import Config
from yapper.controller import Controller
from yapper.hotkey import HotkeyListener
from yapper.mascot import mascot_icon

_SEEN = Path.home() / ".yapper" / ".seen"


def _key_label(spec: str) -> str:
    for k in ("ctrl", "alt", "cmd"):
        if spec.startswith(k):
            return k.capitalize()
    return spec.upper()


def main() -> None:
    cfg = Config.load()
    QApplication.setAttribute(Qt.AA_ShareOpenGLContexts, True)
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    mascot = None
    if cfg.mascot:
        from yapper.mascot import MascotWidget

        def _save_pos(x, y):
            cfg.pos = [x, y]; cfg.save("pos")
        mascot = MascotWidget(size=cfg.size, pos=cfg.pos, on_move=_save_pos)
        mascot.set_state("loading")
        mascot.show()

    controller = Controller(cfg, asr.build(cfg))
    hotkey = HotkeyListener(cfg.hotkey, controller.on_hotkey_start, controller.on_hotkey_stop)

    tray = QSystemTrayIcon(mascot_icon(64))
    tray.setToolTip("Yapper — loading…")
    menu = QMenu()
    act_mascot = QAction("Show mascot", checkable=True); act_mascot.setChecked(cfg.mascot)
    act_quit = QAction("Quit Yapper")
    menu.addAction(act_mascot); menu.addSeparator(); menu.addAction(act_quit)
    tray.setContextMenu(menu)
    tray.show()

    def toggle_mascot(on: bool):
        nonlocal mascot
        cfg.mascot = on; cfg.save("mascot")
        if on:
            if mascot is None:
                from yapper.mascot import MascotWidget
                mascot = MascotWidget(size=cfg.size, pos=cfg.pos,
                                      on_move=lambda x, y: (setattr(cfg, "pos", [x, y]), cfg.save("pos")))
                mascot.set_state("idle" if controller.ready else "loading")
            mascot.show()
        elif mascot is not None:
            mascot.hide()
            tray.showMessage("Yapper", "Mascot hidden — still running in the tray.", mascot_icon(64), 1500)
    act_mascot.toggled.connect(toggle_mascot)

    def quit_app():
        hotkey.stop(); tray.hide(); app.quit()
    act_quit.triggered.connect(quit_app)

    def on_state(state: str):
        if mascot is not None:
            mascot.set_state(state)
        if state == "done":
            QTimer.singleShot(cfg.done_hold_ms, lambda: on_state("idle"))
    controller.sig_state.connect(on_state)

    def on_ready(ok: bool):
        if not ok:
            if mascot is not None:
                mascot.set_state("error")
            tray.setToolTip("Yapper — model load failed (see console).")
            print("[yapper] model load failed - see the message above.", flush=True)
            return
        controller.ready = True
        on_state("idle")
        tray.setToolTip(f"Yapper — {controller.asr.source} on {controller.asr.device}. Hold {cfg.hotkey} to talk.")
        hotkey.start()
        if mascot is not None and not _SEEN.exists():
            mascot.show_ready(f"Press {_key_label(cfg.hotkey)} to yap")
            try:
                _SEEN.parent.mkdir(parents=True, exist_ok=True); _SEEN.write_text("1", "utf-8")
            except Exception:
                pass
        print(f"[yapper] ready | model={controller.asr.source} | device={controller.asr.device} | hold {cfg.hotkey} to talk", flush=True)
    controller.sig_ready.connect(on_ready)

    controller.load_models()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
