"""The Java <-> Python bootstrap protocol."""

import json
import os
import sys
import tempfile
import unittest

import pfm
from pfm import _bridge

from .base import PfmTestCase, purge_support_modules
from .fake_bridge import FakeBridge


class BootstrapTests(unittest.TestCase):
    def setUp(self):
        pfm._shutdown()
        _bridge.reset()
        purge_support_modules()
        self.bridge = FakeBridge("mod_a", "server")
        pfm._install_bridge(self.bridge)

    def tearDown(self):
        pfm._shutdown()
        _bridge.reset()
        purge_support_modules()

    def test_dict_config(self):
        pfm._bootstrap("mod_a", "server", {"metadata": {"loader": "fabric"}})
        self.assertEqual(pfm.runtime().context.metadata["loader"], "fabric")

    def test_json_string_config_is_what_java_sends(self):
        config = json.dumps({
            "metadata": {"loader": "neoforge", "mod_root": "python"},
            "vendor_paths": [],
            "modules": [],
        })
        pfm._bootstrap("mod_a", "server", config)
        self.assertEqual(pfm.runtime().context.metadata["loader"], "neoforge")

    def test_bootstrap_autodiscovers_declared_modules(self):
        config = json.dumps({"metadata": {}, "vendor_paths": [],
                             "modules": ["tests.support.mod_a"]})
        pfm._bootstrap("mod_a", "server", config)
        self.assertEqual(pfm.runtime().handler_count("server_start"), 2)
        self.assertIn("pyhello", pfm.runtime().commands)

    def test_bootstrap_adds_vendor_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(tmp, "bootstrap_probe.py"), "w") as handle:
                handle.write("OK = True\n")
            pfm._bootstrap("mod_a", "server",
                           json.dumps({"metadata": {}, "vendor_paths": [tmp]}))
            try:
                import bootstrap_probe  # noqa: PLC0415

                self.assertTrue(bootstrap_probe.OK)
            finally:
                sys.modules.pop("bootstrap_probe", None)
                from pfm import _deps

                _deps.remove_paths([tmp])

    def test_invalid_json_is_reported(self):
        with self.assertRaises(pfm.PyFmError) as ctx:
            pfm._bootstrap("mod_a", "server", "{not json")
        self.assertIn("not valid JSON", str(ctx.exception))

    def test_empty_and_missing_config_are_accepted(self):
        pfm._bootstrap("mod_a", "server", None)
        self.assertEqual(pfm.runtime().context.metadata, {})
        pfm._shutdown("mod_a")
        pfm._bootstrap("mod_a", "server", "")
        self.assertEqual(pfm.runtime().context.metadata, {})

    def test_unknown_side_is_rejected(self):
        with self.assertRaises(ValueError):
            pfm._bootstrap("mod_a", "sideways", None)

    def test_status_json(self):
        pfm._bootstrap("mod_a", "server",
                       json.dumps({"modules": ["tests.support.mod_a"]}))
        status = json.loads(pfm._status_json())
        self.assertIn("mod_a", status)
        self.assertIn("pyhello", status["mod_a"]["commands"])
        self.assertEqual(status["mod_a"]["handlers"]["server_start"], 2)

    def test_guest_exception_formatting_helper(self):
        pfm._bootstrap("mod_a", "server", None)
        try:
            raise ValueError("from the guest")
        except ValueError as exc:
            text = pfm._format_guest_exception(exc, "mod_a", "initialize")
        self.assertIn("from the guest", text)
        self.assertIn("mod_a", text)


if __name__ == "__main__":
    unittest.main()
