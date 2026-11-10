"""pfm — the public Python API of Python-for-Minecraft.

A Python mod uses only this package::

    import pfm

    @pfm.event("server_start")
    def on_server_start(event):
        pfm.log.info("server %s started" % pfm.mc.server)

    @pfm.command("pyhello", permission=0)
    def hello(ctx):
        ctx.reply("Hello from Python!")

    class PyHelloCommon:
        def on_initialize(self):
            pfm.log.info("PyHelloCommon initialised on the %s side" % pfm.side())

Nothing else in this package is public API; modules starting with ``_`` are internal and
are shared with the Java side only.
"""

from __future__ import annotations

import json
from typing import Any, Callable, Dict, List, Optional

from . import java
from ._bridge import BridgeError
from ._deps import add_paths as _add_paths
from ._handles import mc
from ._bridge import install as _install_bridge
from ._bridge import is_installed as _bridge_installed
from ._context import CommandContext, Event, ModContext, Side
from ._entrypoints import LIFECYCLE, PHASES, Entrypoint
from ._entrypoints import parse as parse_entrypoint
from ._errors import EntrypointError, HandlerError, PyFmError, format_exception
from ._log import Logger, get_logger, log
from ._registry import (CommandSpec, DispatchReport, Handler, ModRuntime, all_runtimes,
                        autodiscover, begin_mod, current_mod_id, dispatch, end_mod,
                        invoke_command, register_command, register_handler, runtime,
                        runtime_for, shutdown)

__version__ = "1.0.0"

__all__ = [
    "__version__", "Side", "Event", "ModContext", "CommandContext", "Handler",
    "CommandSpec", "DispatchReport", "ModRuntime", "Entrypoint", "PyFmError",
    "EntrypointError", "HandlerError", "BridgeError", "format_exception", "log",
    "get_logger", "Logger", "java", "mc", "event", "on", "command", "fire",
    "autodiscover", "register_handler", "register_command", "dispatch", "runtime",
    "runtime_for", "all_runtimes", "mod_id", "side", "is_client", "is_server", "context",
    "parse_entrypoint", "LIFECYCLE", "PHASES",
]


# --------------------------------------------------------------------------- decorators
def event(name: str, *, priority: int = 0, side: str = Side.BOTH,
          mod_id: Optional[str] = None) -> Callable[[Callable], Callable]:
    """Register the decorated function as a handler for event *name*.

    :param name: event name, e.g. ``"server_start"``.  Custom names are allowed and can be
        fired by the mod itself with :func:`fire`.
    :param priority: higher runs first; equal priorities run in registration order.
    :param side: ``Side.CLIENT``, ``Side.SERVER`` or ``Side.BOTH``.  A handler whose side
        does not match the side the runtime runs on is skipped.
    """
    def decorator(func: Callable) -> Callable:
        register_handler(name, func, priority=priority, side=side, mod_id=mod_id)
        return func

    return decorator


on = event


def command(name: str, *, usage: str = "", permission: int = 0, side: str = Side.BOTH,
            mod_id: Optional[str] = None) -> Callable[[Callable], Callable]:
    """Register the decorated function as the callback of the ``/name`` command.

    The command itself is created by the Java side using the loader's own command API; the
    callback receives a :class:`pfm.CommandContext`.
    """
    def decorator(func: Callable) -> Callable:
        register_command(name, func, usage=usage, permission=permission, side=side,
                         mod_id=mod_id)
        return func

    return decorator


# ------------------------------------------------------------------------------- access
def context() -> ModContext:
    """The :class:`ModContext` of the mod currently being initialised."""
    return runtime().context


def mod_id() -> str:
    return runtime().mod_id


def side() -> str:
    return runtime().side


def is_client() -> bool:
    return runtime().side == Side.CLIENT


def is_server() -> bool:
    return runtime().side == Side.SERVER


def fire(name: str, data: Any = None, *, mod_id: Optional[str] = None,
         strict: bool = False) -> DispatchReport:
    """Fire an event inside one mod (used for a mod's own custom events)."""
    return dispatch(name, data, mod_id=mod_id, strict=strict)


# ----------------------------------------------------- protocol used by the Java runtime
def _coerce_metadata(metadata: Any) -> Dict[str, Any]:
    """Accept the mod metadata as a dict or as a JSON document.

    The Java side passes JSON text, because a string crosses the Java/Python boundary
    without depending on Truffle's collection conversions.  Tests may pass a dict.
    """
    if metadata is None:
        return {}
    if isinstance(metadata, str):
        try:
            parsed = json.loads(metadata) if metadata.strip() else {}
        except ValueError as exc:
            raise PyFmError("mod metadata is not valid JSON: {}".format(exc),
                            phase="bootstrap") from exc
        return parsed if isinstance(parsed, dict) else {}
    if isinstance(metadata, dict):
        return dict(metadata)
    items = getattr(metadata, "items", None)
    if callable(items):
        try:
            return dict(items())
        except Exception:  # pragma: no cover - foreign map with an odd shape
            return {}
    return {}


def _bootstrap(mod_id_: str, side_: str, config: Any = None) -> str:
    """Prepare the runtime of one mod.  Called once per mod by the Java side.

    *config* is either a dict or a JSON document with the keys

    ``metadata``     mod metadata, exposed as :attr:`pfm.ModContext.metadata`
    ``vendor_paths`` absolute directories of vendored dependencies, added to ``sys.path``
    ``modules``      packages to import so that ``@pfm.event``/``@pfm.command`` register
    """
    cfg = _coerce_metadata(config)
    rt = begin_mod(mod_id_, side_, cfg.get("metadata") or {})
    # The runtime package (pfm itself) goes first, so a mod cannot shadow it.
    _add_paths([str(p) for p in (cfg.get("runtime_paths") or [])], front=True)
    added = _add_paths([str(p) for p in (cfg.get("vendor_paths") or [])])
    for module in cfg.get("modules") or []:
        autodiscover(str(module), mod_id=mod_id_)
    log.info("Python mod {} bootstrapped on the {} side ({} vendor path(s))".format(
        rt.mod_id, rt.side, len(added)))
    return rt.mod_id


def _autodiscover(module: str, mod_id: Optional[str] = None) -> List[str]:
    return autodiscover(module, mod_id=mod_id)


def _load_entrypoint(spec: str, phase: str, mod_id: Optional[str] = None) -> List[str]:
    """Load *spec* and run *phase* for it.  Raises :class:`EntrypointError` on failure.

    The entry point object is cached per mod and per spec, so the three lifecycle phases
    of one mod share the same instance.
    """
    rt = runtime() if mod_id is None else runtime_for(mod_id)
    begin_mod(rt.mod_id, rt.side, rt.context.metadata)
    entrypoint = rt.entrypoints.get(spec)
    if entrypoint is None:
        entrypoint = Entrypoint(spec, rt.context)
        rt.entrypoints[spec] = entrypoint
    ran = entrypoint.invoke(phase)
    rt.invocations.append((spec, phase))
    if ran:
        log.info("entry point {} ran {} for {}".format(spec, ", ".join(ran), rt.mod_id))
    return ran


def _dispatch(event_name: str, data: Any = None, mod_id: Optional[str] = None) -> str:
    """Dispatch one event; returns a one-line summary for the game log."""
    report = dispatch(event_name, data, mod_id=mod_id)
    return "event={} mod={} invoked={} skipped={} errors={}".format(
        report.event, report.mod_id, report.invoked, report.skipped, len(report.errors))


def _invoke_command(key: str, source: Any, args: Any = None) -> int:
    """Run a command callback registered by a Python mod."""
    return invoke_command(key, source, list(args) if args is not None else None)


def _setup_paths(vendor_paths: Any) -> List[str]:
    """Put vendored dependency directories of one mod on ``sys.path``.

    Called by the Java side right after :func:`_bootstrap`, with the absolute directories
    that the mod's vendored wheels were unpacked into.  No network access happens here.
    """
    if vendor_paths is None:
        return []
    if isinstance(vendor_paths, str):
        vendor_paths = [vendor_paths]
    else:
        vendor_paths = list(vendor_paths)
    return _add_paths(vendor_paths)


def _shutdown(mod_id: Optional[str] = None) -> None:
    """Release handlers, commands and entry points.  Called on game/server stop."""
    if mod_id is not None:
        log.info("shutting down Python mod {}".format(mod_id))
    shutdown(mod_id)


def _status_json() -> str:
    """:func:`_status` serialised, so the Java side can log it as plain text."""
    return json.dumps(_status(), sort_keys=True)


def _format_guest_exception(exc: Any, mod_id: Optional[str] = None,
                            phase: Optional[str] = None) -> str:
    """Format a guest (Python) exception the Java side caught as PolyglotException."""
    return format_exception(exc, mod_id=mod_id, phase=phase)


def _status() -> Dict[str, Any]:
    """Snapshot used by the Java side for logging and diagnostics."""
    return {
        rt.mod_id: {
            "side": rt.side,
            "handlers": {name: len(items) for name, items in rt.handlers.items()},
            "commands": sorted(rt.commands),
            "modules": list(rt.loaded_modules),
        }
        for rt in all_runtimes()
    }
