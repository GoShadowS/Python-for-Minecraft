"""Error reporting for Python-for-Minecraft.

A Python failure must always answer four questions: which mod, which entry point or
handler, which file and line, and what the traceback was.  :func:`format_exception`
is the single place that formats that answer, and it is used both by the Python
dispatcher and (through the bridge) by the Java side.
"""

from __future__ import annotations

import traceback
from typing import Optional

__all__ = ["PyFmError", "EntrypointError", "HandlerError", "format_exception"]


class PyFmError(Exception):
    """Base class for every error raised by the Python-for-Minecraft runtime."""

    def __init__(self, message: str, *, mod_id: Optional[str] = None,
                 phase: Optional[str] = None) -> None:
        super().__init__(message)
        self.mod_id = mod_id
        self.phase = phase


class EntrypointError(PyFmError):
    """Raised when a declared entry point cannot be imported, resolved or invoked."""


class HandlerError(PyFmError):
    """Raised when an event handler or a command callback fails."""


def _origin(exc: BaseException) -> str:
    """Return ``file:line`` of the frame where *exc* was raised, if known."""
    tb = exc.__traceback__
    last = None
    while tb is not None:
        last = tb
        tb = tb.tb_next
    if last is None:
        return "<unknown>:0"
    frame = last.tb_frame
    return "{}:{}".format(frame.f_code.co_filename, frame.f_lineno)


def format_exception(exc: BaseException, *, mod_id: Optional[str] = None,
                     phase: Optional[str] = None,
                     include_traceback: bool = True) -> str:
    """Format *exc* the way Python-for-Minecraft reports it to the game log.

    The first line is always ``[pythonforminecraft] <mod_id>: <phase> failed``, followed
    by the origin ``file:line``, the exception type and message and, unless disabled, the
    full Python traceback.
    """
    head = "[pythonforminecraft] {}: {} failed".format(mod_id or "<unknown mod>",
                                                       phase or "<unknown phase>")
    lines = [head, "  at {}".format(_origin(exc))]
    body = "".join(traceback.format_exception_only(type(exc), exc)).rstrip()
    if body:
        lines.append("  " + body.splitlines()[-1])
    else:
        lines.append("  " + type(exc).__name__)
    if isinstance(exc, PyFmError) and exc.__cause__ is not None:
        lines.append("  caused by {}: {}".format(type(exc.__cause__).__name__,
                                                 exc.__cause__))
    if include_traceback:
        tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        lines.append("  traceback:")
        for line in tb.rstrip().splitlines():
            lines.append("    " + line)
    return "\n".join(lines)
