"""A Python double for the Java bridge (``...core.JavaBridge``).

Every method mirrors the Java contract documented in ``pfm/_bridge.py`` so the Python
layer can be exercised without a JVM.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple


class JavaClassStub:
    """Stands in for a Java ``Class`` handed back by ``import_class``."""

    def __init__(self, name: str) -> None:
        self.name = name

    def getName(self) -> str:  # noqa: N802 - mimics the Java method name
        return self.name

    def __repr__(self) -> str:
        return "JavaClassStub({!r})".format(self.name)


class FakeBridge:
    def __init__(self, mod_id: str = "test_mod", side: str = "server") -> None:
        self._mod_id = mod_id
        self._side = side
        self.logs: List[Tuple[str, str]] = []
        self.commands: List[Dict[str, Any]] = []
        self.replies: List[Tuple[Any, str]] = []
        self.failures: List[str] = []
        self.classes: Dict[str, Any] = {}
        self.handles: Dict[str, Any] = {}

    # -- bridge contract --------------------------------------------------
    def mod_id(self) -> str:
        return self._mod_id

    def side(self) -> str:
        return self._side

    def log(self, level: str, message: str) -> None:
        self.logs.append((level, message))

    def register_command(self, name: str, key: str, usage: str, permission: int,
                         side: str) -> None:
        self.commands.append({"name": name, "key": key, "usage": usage,
                              "permission": permission, "side": side})

    def reply(self, source: Any, text: str) -> None:
        self.replies.append((source, text))

    def import_class(self, name: str) -> Any:
        return self.classes.get(name, JavaClassStub(name))

    def get_handle(self, name: str) -> Optional[Any]:
        return self.handles.get(name)

    def fail(self, message: str) -> None:
        self.failures.append(message)

    # -- test helpers -----------------------------------------------------
    def messages(self, level: Optional[str] = None) -> List[str]:
        return [m for lvl, m in self.logs if level is None or lvl == level]

    def text(self) -> str:
        return "\n".join(m for _, m in self.logs)
