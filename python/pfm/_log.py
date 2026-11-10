"""Logging for Python mods.

Goes through the bridge so that Python messages land in the game log with the mod id as
prefix, and fall back to the stdlib ``logging`` module when no bridge is present (tests,
tooling).
"""

from __future__ import annotations

import logging
from typing import Optional

from . import _bridge

__all__ = ["Logger", "get_logger"]

_STDLIB = logging.getLogger("pythonforminecraft")


class Logger:
    """A tiny level-based logger bound to one mod id."""

    def __init__(self, mod_id: Optional[str] = None) -> None:
        self._mod_id = mod_id

    def _emit(self, level: str, message: object) -> None:
        text = str(message)
        if _bridge.is_installed():
            _bridge.bridge().log(level, text)
        else:
            getattr(_STDLIB, "warning" if level == "warn" else level)(
                "[%s] %s", self._mod_id or "pythonforminecraft", text)

    def debug(self, message: object) -> None:
        self._emit("debug", message)

    def info(self, message: object) -> None:
        self._emit("info", message)

    def warn(self, message: object) -> None:
        self._emit("warn", message)

    warning = warn

    def error(self, message: object) -> None:
        self._emit("error", message)


log = Logger()


def get_logger(mod_id: Optional[str] = None) -> Logger:
    return Logger(mod_id)
