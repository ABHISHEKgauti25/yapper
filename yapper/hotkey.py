"""
Global push-to-talk hotkey via pynput. Fires on_start when the chosen key goes down and
on_stop when it is released. Auto-repeat while held is de-bounced.

Default key is Right Ctrl (`ctrl_r`) so normal Ctrl+C/V shortcuts keep working.
"""
from __future__ import annotations

from typing import Callable

from pynput import keyboard

# config string -> pynput Key
_KEYMAP = {
    "ctrl_r": keyboard.Key.ctrl_r,
    "ctrl_l": keyboard.Key.ctrl_l,
    "alt_r": keyboard.Key.alt_r,
    "alt_l": keyboard.Key.alt_l,
    "cmd_r": keyboard.Key.cmd_r,
    "cmd": keyboard.Key.cmd,
    "f9": keyboard.Key.f9,
    "f8": keyboard.Key.f8,
    "pause": keyboard.Key.pause,
    "scroll_lock": keyboard.Key.scroll_lock,
}


def resolve_key(spec: str):
    if spec in _KEYMAP:
        return _KEYMAP[spec]
    if len(spec) == 1:                       # a single character key, e.g. "`"
        return keyboard.KeyCode.from_char(spec)
    raise ValueError(f"unknown hotkey {spec!r}; options: {', '.join(_KEYMAP)} or a single char")


class HotkeyListener:
    def __init__(self, key_spec: str, on_start: Callable[[], None], on_stop: Callable[[], None]):
        self._key = resolve_key(key_spec)
        self._on_start = on_start
        self._on_stop = on_stop
        self._down = False
        self._listener: keyboard.Listener | None = None

    def _match(self, key) -> bool:
        return key == self._key

    def _press(self, key):
        if self._match(key) and not self._down:   # ignore auto-repeat
            self._down = True
            self._on_start()

    def _release(self, key):
        if self._match(key) and self._down:
            self._down = False
            self._on_stop()

    def start(self) -> None:
        self._listener = keyboard.Listener(on_press=self._press, on_release=self._release)
        self._listener.start()

    def stop(self) -> None:
        if self._listener is not None:
            self._listener.stop()
            self._listener = None
