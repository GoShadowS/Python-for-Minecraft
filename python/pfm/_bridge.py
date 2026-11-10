"""The Java <-> Python bridge.

The Java side of Python-for-Minecraft injects a *bridge* object into the Python runtime
right after the context is created::

    Value pfm = context.eval("python", "import pfm; pfm");
    pfm.invokeMember("_install_bridge", javaBridge);

The bridge is a Java object; GraalPy exposes it as a foreign object whose methods can be
called like ordinary Python methods.  Tests inject a plain Python double instead, which is
why every interaction goes through this module and never touches Java types directly.

Bridge contract (implemented by ``io.github.goshadows.pythonforminecraft.core.JavaBridge``):

    mod_id() -> str                       mod id this bridge belongs to
    side() -> str                         "client" | "server"
    log(level, message)                   level: debug|info|warn|error
    register_command(name, key, usage, permission, side)   all primitives
    reply(source, text)                   send text back to a command source
    import_class(fqcn) -> object          Java interop: look up a Java class
    get_handle(name) -> object            "server" | "client" | "player" | ...
    fail(message)                         report a fatal Python-side failure to the loader
"""

from __future__ import annotations

from typing import Any, Optional

__all__ = ["BridgeError", "install", "bridge", "is_installed", "reset"]

_BRIDGE: Optional[Any] = None


class BridgeError(RuntimeError):
    """Raised when Python code needs the bridge but none was installed."""


def install(obj: Any) -> None:
    """Install *obj* as the bridge.  Called by the Java bootstrap and by tests."""
    global _BRIDGE
    _BRIDGE = obj


def reset() -> None:
    """Remove any installed bridge (used by tests and by shutdown)."""
    global _BRIDGE
    _BRIDGE = None


def is_installed() -> bool:
    return _BRIDGE is not None or _from_polyglot() is not None


def _from_polyglot() -> Optional[Any]:
    """Fallback: read the bridge from the polyglot bindings (GraalPy only)."""
    try:
        import polyglot  # type: ignore[import-not-found]
    except Exception:
        return None
    try:
        return polyglot.import_value("_pfm_bridge")
    except Exception:
        return None


def bridge() -> Any:
    """Return the installed bridge, falling back to the polyglot bindings."""
    if _BRIDGE is not None:
        return _BRIDGE
    found = _from_polyglot()
    if found is not None:
        install(found)
        return found
    raise BridgeError(
        "the Python-for-Minecraft bridge is not installed; this module can only be used "
        "inside a Python mod loaded by Python-for-Minecraft (or with a test double "
        "installed through pfm._install_bridge)")
