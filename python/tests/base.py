"""Shared test fixture: a fake bridge plus one bootstrapped mod runtime."""

from __future__ import annotations

import importlib
import sys
import unittest

import pfm
from pfm import _bridge

from .fake_bridge import FakeBridge


def purge_support_modules() -> None:
    """Drop the support packages from ``sys.modules``.

    A real Python mod gets a fresh GraalPy context, so its modules are imported again for
    every mod.  Tests run in one CPython process, so the import cache has to be cleared
    explicitly for decorator registration to happen against the current runtime.
    """
    for name in [n for n in sys.modules if n.startswith("tests.support")]:
        del sys.modules[name]


def support(name: str):
    """Import (or re-import) a support package module after the cache was purged."""
    return importlib.import_module(name)


class PfmTestCase(unittest.TestCase):
    mod_id = "mod_a"
    side = "server"

    def setUp(self) -> None:
        pfm._shutdown()
        _bridge.reset()
        purge_support_modules()
        self.bridge = FakeBridge(self.mod_id, self.side)
        pfm._install_bridge(self.bridge)
        pfm._bootstrap(self.mod_id, self.side,
                       {"metadata": {"python_root": "python", "loader": "test"},
                        "vendor_paths": [],
                        "modules": []})

    def tearDown(self) -> None:
        pfm._shutdown()
        _bridge.reset()
        purge_support_modules()
