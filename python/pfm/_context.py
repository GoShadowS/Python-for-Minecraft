"""Side and per-mod context objects."""

from __future__ import annotations

from typing import Any, Dict, Optional

__all__ = ["Side", "Event", "CommandContext", "ModContext"]


class Side:
    """Which physical side a piece of code runs on."""

    CLIENT = "client"
    SERVER = "server"
    BOTH = "both"

    _ALL = (CLIENT, SERVER, BOTH)

    @classmethod
    def validate(cls, value: str) -> str:
        if value not in cls._ALL:
            raise ValueError("unknown side {!r}, expected one of {}".format(
                value, ", ".join(cls._ALL)))
        return value

    @classmethod
    def matches(cls, declared: str, actual: str) -> bool:
        """True when a handler declared for *declared* may run on *actual*."""
        return declared == cls.BOTH or declared == actual


class Event:
    """Payload handed to every event handler.

    ``data`` is whatever the Java side passes for that event: a Java object (visible to
    Python through interop) or, in tests, a plain dict.
    """

    __slots__ = ("name", "data", "mod_id")

    def __init__(self, name: str, data: Any = None, mod_id: Optional[str] = None) -> None:
        self.name = name
        self.data = data
        self.mod_id = mod_id

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return "Event(name={!r}, mod_id={!r})".format(self.name, self.mod_id)


class CommandContext:
    """Argument passed to a ``@pfm.command`` callback.

    ``source`` is the loader's command source object (Java interop).  ``reply`` sends a
    message back through the bridge.
    """

    __slots__ = ("source", "_bridge", "args")

    def __init__(self, source: Any, bridge: Any, args: Optional[list] = None) -> None:
        self.source = source
        self._bridge = bridge
        self.args = list(args or [])

    def reply(self, text: object) -> None:
        self._bridge.reply(self.source, str(text))

    def arg(self, index: int, default: Any = None) -> Any:
        return self.args[index] if index < len(self.args) else default


class ModContext:
    """Everything Python code can ask about the mod it belongs to."""

    __slots__ = ("mod_id", "side", "metadata")

    def __init__(self, mod_id: str, side: str, metadata: Optional[Dict[str, Any]] = None
                 ) -> None:
        self.mod_id = mod_id
        self.side = Side.validate(side)
        self.metadata = dict(metadata or {})

    def is_client(self) -> bool:
        return self.side == Side.CLIENT

    def is_server(self) -> bool:
        return self.side == Side.SERVER

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return "ModContext(mod_id={!r}, side={!r})".format(self.mod_id, self.side)
