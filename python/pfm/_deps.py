"""Python dependency paths.

Python-for-Minecraft never downloads anything while the game runs.  Third-party packages
are vendored at build time (see ``tools/vendor_deps.py`` and
``docs/python-dependencies.md``) and shipped inside the mod jar; at start-up their
directories are simply put on ``sys.path``.
"""

from __future__ import annotations

import os
import sys
from typing import Iterable, List

__all__ = ["add_paths", "remove_paths", "current_paths"]


def add_paths(paths: Iterable[str], *, front: bool = True) -> List[str]:
    """Put every existing directory of *paths* on ``sys.path`` (idempotently).

    Missing directories are skipped rather than fatal: a mod that vendors nothing simply
    has no vendor directory.
    """
    added: List[str] = []
    for raw in paths or ():
        path = os.path.abspath(str(raw))
        if not os.path.isdir(path):
            continue
        if path in sys.path:
            continue
        if front:
            sys.path.insert(0, path)
        else:
            sys.path.append(path)
        added.append(path)
    return added


def remove_paths(paths: Iterable[str]) -> List[str]:
    """Remove *paths* from ``sys.path`` again (used when a mod is unloaded)."""
    removed: List[str] = []
    for raw in paths or ():
        path = os.path.abspath(str(raw))
        while path in sys.path:
            sys.path.remove(path)
            removed.append(path)
    return removed


def current_paths() -> List[str]:
    return list(sys.path)
