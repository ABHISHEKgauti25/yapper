"""Send a Ctrl+V to the focused window (used after putting text on the clipboard).

Uses the generic (left) Ctrl so it never collides with a Right-Ctrl push-to-talk hotkey.
"""
from __future__ import annotations

import time

from pynput.keyboard import Controller, Key

_kb = Controller()


def send_ctrl_v() -> None:
    # small settle so the target app has focus and the clipboard is ready
    time.sleep(0.03)
    _kb.press(Key.ctrl)
    _kb.press("v")
    _kb.release("v")
    _kb.release(Key.ctrl)
