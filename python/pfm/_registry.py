"""Per-mod handler/command registries and event dispatch.

Python-for-Minecraft normally creates **one GraalPy context per Python mod**, which already
isolates modules and globals.  On top of that every registry here is keyed by mod id, so the
same semantics also hold in ``shared`` isolation mode (one context, several mods) and can be
exercised by tests inside a single CPython process.
"""

from __future__ import annotations

import importlib
import pkgutil
from contextvars import ContextVar
from typing import Any, Callable, Dict, List, Optional, Tuple

from . import _bridge
from ._context import Event, ModContext, Side
from ._errors import HandlerError, format_exception
from ._log import log

__all__ = [
    "Handler", "CommandSpec", "ModRuntime", "DispatchReport",
    "begin_mod", "end_mod", "current_mod_id", "runtime", "runtime_for", "all_runtimes",
    "register_handler", "register_command", "dispatch", "invoke_command",
    "autodiscover", "shutdown",
]

# Well known event names.  Anything else is accepted too: a Python mod may define its own
# events and fire them with pfm.fire().
EVENTS = (
    "initialize",
    "client_initialize",
    "server_initialize",
    "client_start",
    "client_stop",
    "server_start",
    "server_stop",
    "client_tick",
    "server_tick",
    "player_join",
    "player_leave",
)


class Handler:
    __slots__ = ("event", "func", "priority", "side", "module")

    def __init__(self, event: str, func: Callable, priority: int = 0,
                 side: str = Side.BOTH, module: Optional[str] = None) -> None:
        self.event = event
        self.func = func
        self.priority = priority
        self.side = Side.validate(side)
        self.module = module

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return "Handler(event={!r}, func={!r}, priority={!r}, side={!r})".format(
            self.event, getattr(self.func, "__name__", self.func), self.priority, self.side)


class CommandSpec:
    __slots__ = ("name", "callback", "usage", "permission", "side", "module")

    def __init__(self, name: str, callback: Callable, usage: str = "", permission: int = 0,
                 side: str = Side.BOTH, module: Optional[str] = None) -> None:
        if not name or " " in name or name.startswith("/"):
            raise ValueError("command name must be a single word without a leading slash")
        self.name = name
        self.callback = callback
        self.usage = usage or "/" + name
        self.permission = int(permission)
        self.side = Side.validate(side)
        self.module = module

    def key(self, mod_id: str) -> str:
        """Stable identifier used by the Java side to call this callback back."""
        return "{}:{}".format(mod_id, self.name)

    def as_dict(self, mod_id: str) -> Dict[str, Any]:
        return {
            "name": self.name,
            "key": self.key(mod_id),
            "usage": self.usage,
            "permission": self.permission,
            "side": self.side,
        }

    def as_args(self, mod_id: str) -> tuple:
        """Positional primitive arguments for ``bridge.register_command``.

        Only strings and ints cross the boundary, so the Java side does not depend on
        Truffle converting a Python dict into a ``Map``.
        """
        return (self.name, self.key(mod_id), self.usage, self.permission, self.side)


class DispatchReport:
    """Result of dispatching one event: how many handlers ran and what failed."""

    __slots__ = ("event", "mod_id", "invoked", "skipped", "errors")

    def __init__(self, event: str, mod_id: str) -> None:
        self.event = event
        self.mod_id = mod_id
        self.invoked = 0
        self.skipped = 0
        self.errors: List[str] = []

    @property
    def ok(self) -> bool:
        return not self.errors

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return ("DispatchReport(event={!r}, mod_id={!r}, invoked={}, skipped={}, "
                "errors={})").format(self.event, self.mod_id, self.invoked, self.skipped,
                                     len(self.errors))


class ModRuntime:
    """The registry of one Python mod."""

    def __init__(self, context: ModContext) -> None:
        self.context = context
        self.handlers: Dict[str, List[Handler]] = {}
        self.commands: Dict[str, CommandSpec] = {}
        # spec -> Entrypoint; one instance per declared entry point, so that all lifecycle
        # phases of a mod share the same object.
        self.entrypoints: Dict[str, Any] = {}
        self.invocations: List[Tuple[str, str]] = []
        self.loaded_modules: List[str] = []
        self.closed = False

    @property
    def mod_id(self) -> str:
        return self.context.mod_id

    @property
    def side(self) -> str:
        return self.context.side

    # -- registration -----------------------------------------------------
    def add_handler(self, handler: Handler) -> Handler:
        if self.closed:
            raise HandlerError("mod {} is already shut down".format(self.mod_id),
                               mod_id=self.mod_id, phase=handler.event)
        bucket = self.handlers.setdefault(handler.event, [])
        bucket.append(handler)
        bucket.sort(key=lambda h: (-h.priority,))
        return handler

    def add_command(self, spec: CommandSpec) -> CommandSpec:
        if self.closed:
            raise HandlerError("mod {} is already shut down".format(self.mod_id),
                               mod_id=self.mod_id, phase="command:" + spec.name)
        existing = self.commands.get(spec.name)
        if existing is not None:
            raise HandlerError(
                "command /{} is already registered by {}".format(
                    spec.name, existing.module or "<unknown>"),
                mod_id=self.mod_id, phase="command:" + spec.name)
        self.commands[spec.name] = spec
        if _bridge.is_installed():
            _bridge.bridge().register_command(*spec.as_args(self.mod_id))
        return spec

    def handler_count(self, event: Optional[str] = None) -> int:
        if event is None:
            return sum(len(v) for v in self.handlers.values())
        return len(self.handlers.get(event, []))

    # -- dispatch ---------------------------------------------------------
    def dispatch(self, event: str, data: Any = None, strict: bool = False
                 ) -> DispatchReport:
        report = DispatchReport(event, self.mod_id)
        for handler in list(self.handlers.get(event, ())):
            if not Side.matches(handler.side, self.side):
                report.skipped += 1
                continue
            payload = Event(event, data, self.mod_id)
            try:
                _call(handler.func, payload)
                report.invoked += 1
            except Exception as exc:  # noqa: BLE001 - reported, never swallowed silently
                text = format_exception(exc, mod_id=self.mod_id,
                                        phase="event " + event)
                report.errors.append(text)
                log.error(text)
                if strict:
                    raise
        return report

    def invoke_command(self, name: str, source: Any, args: Optional[list] = None) -> int:
        spec = self.commands.get(name)
        if spec is None:
            raise HandlerError("no such command /{}".format(name), mod_id=self.mod_id,
                               phase="command:" + name)
        if not Side.matches(spec.side, self.side):
            raise HandlerError(
                "command /{} is not available on the {} side".format(name, self.side),
                mod_id=self.mod_id, phase="command:" + name)
        ctx = _make_command_context(source, args)
        try:
            _call(spec.callback, ctx)
            return 1
        except Exception as exc:  # noqa: BLE001 - surfaced to the command source
            log.error(format_exception(exc, mod_id=self.mod_id,
                                       phase="command /" + name))
            raise

    def close(self) -> None:
        self.handlers.clear()
        self.commands.clear()
        self.entrypoints.clear()
        self.invocations.clear()
        self.loaded_modules.clear()
        self.closed = True


def _call(func: Callable, payload: Any) -> Any:
    """Call *func* with *payload*, tolerating handlers that take no argument."""
    try:
        return func(payload)
    except TypeError:
        # A zero-argument handler is allowed; distinguish "wrong arity" from a TypeError
        # raised inside the handler by retrying only when the handler takes no parameters.
        import inspect

        try:
            params = [p for p in inspect.signature(func).parameters.values()
                      if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)]
        except (TypeError, ValueError):
            raise
        if params:
            raise
        return func()


def _make_command_context(source: Any, args: Optional[list]):
    from ._context import CommandContext

    return CommandContext(source, _bridge.bridge() if _bridge.is_installed() else None,
                          args)


# -- process wide state ---------------------------------------------------

_RUNTIMES: Dict[str, ModRuntime] = {}
_CURRENT: ContextVar[Optional[str]] = ContextVar("pfm_current_mod", default=None)


def begin_mod(mod_id: str, side: str, metadata: Optional[Dict[str, Any]] = None
              ) -> ModRuntime:
    """Start (or re-enter) the runtime of *mod_id* and make it the current one."""
    runtime = _RUNTIMES.get(mod_id)
    if runtime is None or runtime.closed:
        runtime = ModRuntime(ModContext(mod_id, side, metadata))
        _RUNTIMES[mod_id] = runtime
    _CURRENT.set(mod_id)
    return runtime


def end_mod(mod_id: Optional[str] = None) -> None:
    """Leave the current mod scope without tearing anything down."""
    if mod_id is None:
        _CURRENT.set(None)
    elif _CURRENT.get() == mod_id:
        _CURRENT.set(None)


def current_mod_id() -> Optional[str]:
    return _CURRENT.get()


def runtime_for(mod_id: str) -> ModRuntime:
    try:
        return _RUNTIMES[mod_id]
    except KeyError:
        raise HandlerError("no runtime for Python mod {!r}".format(mod_id), mod_id=mod_id,
                           phase="lookup") from None


def runtime() -> ModRuntime:
    """The runtime of the mod currently being initialised."""
    mod_id = _CURRENT.get()
    if mod_id is None:
        raise HandlerError(
            "no current Python mod; pfm.event()/pfm.command() can only be used while "
            "Python-for-Minecraft is initialising a mod (or pass mod_id explicitly)",
            phase="registration")
    return runtime_for(mod_id)


def all_runtimes() -> Tuple[ModRuntime, ...]:
    return tuple(_RUNTIMES.values())


def _resolve(mod_id: Optional[str]) -> ModRuntime:
    return runtime_for(mod_id) if mod_id is not None else runtime()


def register_handler(event: str, func: Callable, *, priority: int = 0,
                     side: str = Side.BOTH, mod_id: Optional[str] = None) -> Handler:
    handler = Handler(event, func, priority, side,
                      getattr(func, "__module__", None))
    return _resolve(mod_id).add_handler(handler)


def register_command(name: str, callback: Callable, *, usage: str = "", permission: int = 0,
                     side: str = Side.BOTH, mod_id: Optional[str] = None) -> CommandSpec:
    spec = CommandSpec(name, callback, usage, permission, side,
                       getattr(callback, "__module__", None))
    return _resolve(mod_id).add_command(spec)


def dispatch(event: str, data: Any = None, *, mod_id: Optional[str] = None,
             strict: bool = False) -> DispatchReport:
    return _resolve(mod_id).dispatch(event, data, strict=strict)


def invoke_command(key_or_name: str, source: Any, args: Optional[list] = None) -> int:
    """Called by Java when a registered command runs.

    Accepts either the plain command name (``"pyhello"``) or the ``"<modId>:<name>"`` key
    that :meth:`CommandSpec.key` produced, so the Java side can dispatch without knowing
    which mod owns the command.
    """
    if ":" in key_or_name:
        mod_id, _, name = key_or_name.partition(":")
        return runtime_for(mod_id).invoke_command(name, source, args)
    return runtime().invoke_command(key_or_name, source, args)


def autodiscover(package: Optional[str] = None, *, mod_id: Optional[str] = None,
                 include: Optional[List[str]] = None) -> List[str]:
    """Import every module of *package* so that decorators register themselves.

    This is the Python equivalent of KFF's ``AutoKotlinEventBusSubscriber``: handlers are
    found by importing, not by scanning bytecode.  Returns the imported module names.
    """
    rt = _resolve(mod_id)
    if package is None:
        package = rt.mod_id
    root = importlib.import_module(package)
    loaded = [root.__name__]
    search = getattr(root, "__path__", None)
    if search is not None:
        for info in pkgutil.walk_packages(search, prefix=root.__name__ + "."):
            name = info.name
            if include is not None and not any(name.startswith(p) for p in include):
                continue
            if name in loaded:
                continue
            importlib.import_module(name)
            loaded.append(name)
    for name in loaded:
        if name not in rt.loaded_modules:
            rt.loaded_modules.append(name)
    return loaded


def shutdown(mod_id: Optional[str] = None) -> None:
    """Close one runtime, or all of them when *mod_id* is ``None``."""
    if mod_id is not None:
        rt = _RUNTIMES.pop(mod_id, None)
        if rt is not None:
            rt.close()
        return
    for rt in list(_RUNTIMES.values()):
        rt.close()
    _RUNTIMES.clear()
    _CURRENT.set(None)
