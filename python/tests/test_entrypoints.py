import os
import unittest

import pfm
from pfm import EntrypointError

from .base import PfmTestCase, support

SPEC = "tests.support.mod_a.entry:"


class ParseTests(unittest.TestCase):
    def test_valid_specs(self):
        self.assertEqual(pfm.parse_entrypoint("a.b.c:Thing"), ("a.b.c", "Thing"))
        self.assertEqual(pfm.parse_entrypoint("mymod.entry:main"),
                         ("mymod.entry", "main"))

    def test_invalid_specs(self):
        for bad in ["", "no_colon", "mod:attr:extra", ":attr", "mod:", "9mod:attr",
                    "mod:9attr", "mod.sub:attr extra", "mod:attr.name"]:
            with self.subTest(spec=bad):
                with self.assertRaises(EntrypointError):
                    pfm.parse_entrypoint(bad)


class EntrypointTests(PfmTestCase):
    def setUp(self):
        super().setUp()
        self.entry = support("tests.support.mod_a.entry")
        self.entry.reset()

    def test_class_entrypoint_is_constructed_and_hooked(self):
        ran = pfm._load_entrypoint(SPEC + "ModA", "initialize")
        self.assertIn("<construct>", ran)
        self.assertIn("on_initialize", ran)
        self.assertEqual(self.entry.STATE["calls"], ["construct", "initialize"])

    def test_all_three_phases_on_one_instance(self):
        pfm._load_entrypoint(SPEC + "ModA", "initialize")
        pfm._load_entrypoint(SPEC + "ModA", "client_initialize")
        pfm._load_entrypoint(SPEC + "ModA", "server_initialize")
        self.assertEqual(self.entry.STATE["calls"],
                         ["construct", "initialize", "client_initialize",
                          "server_initialize"])

    def test_phase_only_runs_its_own_hook(self):
        ran = pfm._load_entrypoint(SPEC + "ModA", "server_initialize")
        self.assertEqual(ran, ["<construct>", "on_server_initialize"])

    def test_zero_argument_function_entrypoint(self):
        ran = pfm._load_entrypoint(SPEC + "plain_function", "initialize")
        self.assertEqual(ran, ["<call>"])
        self.assertIn("function", self.entry.STATE["calls"])

    def test_function_entrypoint_receives_mod_context(self):
        pfm._load_entrypoint(SPEC + "function_with_context", "initialize")
        self.assertIn("function:" + self.mod_id, self.entry.STATE["calls"])

    def test_class_entrypoint_receives_mod_context(self):
        pfm._load_entrypoint(SPEC + "ModAWithContext", "initialize")
        self.assertIn("construct:" + self.mod_id, self.entry.STATE["calls"])

    def test_factory_entrypoint_hooks_are_used(self):
        pfm._load_entrypoint(SPEC + "factory", "client_initialize")
        self.assertEqual(self.entry.STATE["calls"],
                         ["construct", "client_initialize"])

    def test_unknown_module(self):
        with self.assertRaises(EntrypointError) as ctx:
            pfm._load_entrypoint("tests.support.does_not_exist:Thing", "initialize")
        self.assertIn("does_not_exist", str(ctx.exception))
        self.assertEqual(ctx.exception.mod_id, self.mod_id)
        self.assertEqual(ctx.exception.phase, "import")

    def test_unknown_attribute(self):
        with self.assertRaises(EntrypointError) as ctx:
            pfm._load_entrypoint("tests.support.missing_attr:Nope", "initialize")
        self.assertIn("Nope", str(ctx.exception))
        self.assertEqual(ctx.exception.phase, "resolve")

    def test_unknown_phase(self):
        with self.assertRaises(EntrypointError):
            pfm._load_entrypoint(SPEC + "ModA", "sideways")

    def test_failure_reports_mod_file_and_line(self):
        with self.assertRaises(EntrypointError) as ctx:
            pfm._load_entrypoint("tests.support.broken.entry:Broken", "initialize")
        text = str(ctx.exception)
        origin = os.path.abspath(os.path.join(
            os.path.dirname(__file__), "support", "broken", "entry.py"))
        self.assertIn("mod_a", text)
        self.assertIn("intentional failure", text)
        self.assertIn("ValueError", text)
        self.assertIn(os.path.join("broken", "entry.py"), text)
        self.assertIn("line 6", text)
        self.assertTrue(os.path.exists(origin))
        self.assertIn("traceback:", text)


if __name__ == "__main__":
    unittest.main()
