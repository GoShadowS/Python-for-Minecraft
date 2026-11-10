"""Entry point resolution: ``"package.module:attribute"``.

One notation, identical on Fabric and NeoForge.  The attribute may be

* a callable   -> called with no arguments (or with the :class:`pfm.ModContext` when the
                  callable declares exactly one parameter);
* a class      -> instantiated the same way, then its lifecycle hooks are called;
* an object    -> its lifecycle hooks are called.

Lifecycle hooks: ``on_initialize`` (common), ``on_client_initialize`` (client),
``on_server_initialize`` (dedicated server).
"""

from __future__ import annotations

import importlib
import inspect
import re
from typing import Any, List, Optional

from ._context import ModContext
from ._errors import EntrypointError, format_exception
from ._log import log

__all__ = ["Entrypoint", "parse", "LIFECYCLE", "PHASES"]

SPEC_RE = re.compile(
    r"^(?P<module>[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*)"
    r":(?P<attr>[A-Za-z_][A-Za-z0-9_]*)$")

LIFECYCLE = {
    "initialize": "on_initialize",
    "client_initialize": "on_client_initialize",
    "server_initialize": "on_server_initialize",
}

PHASES = tuple(LIFECYCLE)


def parse(spec: str) -> "tuple[str, str]":
    """Split *spec* into ``(module, attribute)`` or raise :class:`EntrypointError`."""
    if not isinstance(spec, str):
        raise EntrypointError("entry point must be a string, got {!r}".format(type(spec)))
    match = SPEC_RE.match(spec.strip())
    if match is None:
        raise EntrypointError(
            "invalid entry point {!r}: expected 'package.module:attribute'".format(spec))
    return match.group("module"), match.group("attr")


def _arity_accepts_one(func: Any) -> bool:
    try:
        params = [p for p in inspect.signature(func).parameters.values()
                  if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)]
    except (TypeError, ValueError):
        return False
    return len(params) >= 1


def _call_maybe_with_context(target: Any, context: ModContext) -> Any:
    if _arity_accepts_one(target):
        return target(context)
    return target()


class Entrypoint:
    """One declared entry point of one mod."""

    def __init__(self, spec: str, context: ModContext) -> None:
        self.spec = spec
        self.context = context
        self.module_name, self.attr_name = parse(spec)
        self.target: Optional[Any] = None
        self.instance: Optional[Any] = None
        self.invoked: List[str] = []

    # -- loading ----------------------------------------------------------
    def load(self) -> Any:
        """Import the module and resolve the attribute.  Idempotent."""
        if self.target is not None:
            return self.target
        try:
            module = importlib.import_module(self.module_name)
        except Exception as exc:
            raise EntrypointError(
                "could not import module {!r} declared by entry point {!r}: {}".format(
                    self.module_name, self.spec, exc),
                mod_id=self.context.mod_id, phase="import") from exc
        try:
            target = getattr(module, self.attr_name)
        except AttributeError as exc:
            raise EntrypointError(
                "module {!r} has no attribute {!r} (entry point {!r})".format(
                    self.module_name, self.attr_name, self.spec),
                mod_id=self.context.mod_id, phase="resolve") from exc
        self.target = target
        return target

    # -- invocation -------------------------------------------------------
    def invoke(self, phase: str) -> List[str]:
        """Run *phase* for this entry point and return the hook names that ran."""
        if phase not in LIFECYCLE:
            raise EntrypointError("unknown phase {!r}, expected one of {}".format(
                phase, ", ".join(PHASES)), mod_id=self.context.mod_id, phase=phase)
        target = self.load()
        ran: List[str] = []
        try:
            if self.instance is None:
                if inspect.isclass(target):
                    self.instance = _call_maybe_with_context(target, self.context)
                    ran.append("<construct>")
                elif callable(target):
                    result = _call_maybe_with_context(target, self.context)
                    ran.append("<call>")
                    # A factory may return an object that carries lifecycle hooks.
                    self.instance = result if _has_any_hook(result) else None
                else:
                    self.instance = target
            if self.instance is not None:
                hook = LIFECYCLE[phase]
                method = getattr(self.instance, hook, None)
                if callable(method):
                    method()
                    ran.append(hook)
        except EntrypointError:
            raise
        except Exception as exc:
            raise EntrypointError(
                "entry point {!r} failed during {!r}:\n{}".format(
                    self.spec, phase, format_exception(
                        exc, mod_id=self.context.mod_id, phase=phase)),
                mod_id=self.context.mod_id, phase=phase) from exc
        if not ran:
            log.debug("entry point {} has nothing to do for phase {}".format(
                self.spec, phase))
        self.invoked.extend(ran)
        return ran


def _has_any_hook(obj: Any) -> bool:
    return any(callable(getattr(obj, hook, None)) for hook in LIFECYCLE.values())
