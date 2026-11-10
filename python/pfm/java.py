"""Java interop for Python mods.

Two ways to reach Java:

1. GraalPy's own ``java`` module, available inside a GraalPy context::

       import java
       BigInteger = java.type("java.math.BigInteger")

2. :func:`pfm.java.import_class`, which asks the Java side to resolve the class and hand
   it back.  It works through the bridge and is therefore testable outside GraalPy.
"""

from __future__ import annotations

from typing import Any, Optional

from . import _bridge

__all__ = ["import_class", "type_", "is_available", "native_java_module"]


def import_class(fully_qualified_name: str) -> Any:
    """Resolve a Java class through the bridge."""
    return _bridge.bridge().import_class(fully_qualified_name)


type_ = import_class


def native_java_module() -> Optional[Any]:
    """Return GraalPy's ``java`` module when running inside GraalPy, else ``None``."""
    try:
        import java  # type: ignore[import-not-found]
    except Exception:
        return None
    return java


def is_available() -> bool:
    """True when Java interop can be used right now."""
    return native_java_module() is not None or _bridge.is_installed()
