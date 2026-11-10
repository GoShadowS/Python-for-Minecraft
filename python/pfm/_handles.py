"""Handles to the running game.

Handles are resolved lazily through the bridge, because the objects they point at (the
``MinecraftServer``, the ``Minecraft`` client) only exist at certain moments of the game
life cycle and are ``None`` outside of them.
"""

from __future__ import annotations

from typing import Any

from . import _bridge

__all__ = ["mc", "handle"]

KNOWN = ("server", "client", "player")


def handle(name: str) -> Any:
    """Return the Java object registered under *name*, or ``None``."""
    if not _bridge.is_installed():
        return None
    return _bridge.bridge().get_handle(name)


class _Handles:
    """Attribute access to the well known handles."""

    @property
    def server(self) -> Any:
        return handle("server")

    @property
    def client(self) -> Any:
        return handle("client")

    @property
    def player(self) -> Any:
        return handle("player")

    def __getattr__(self, name: str) -> Any:
        if name.startswith("_"):
            raise AttributeError(name)
        return handle(name)


mc = _Handles()
