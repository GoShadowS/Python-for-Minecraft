import os
import unittest

import pfm

from .base import PfmTestCase


class TracebackTests(PfmTestCase):
    def test_format_exception_contains_the_four_answers(self):
        try:
            raise ValueError("bad value")
        except ValueError as exc:
            text = pfm.format_exception(exc, mod_id="mod_x", phase="event server_start")

        self.assertIn("[pythonforminecraft] mod_x: event server_start failed", text)
        self.assertIn("ValueError: bad value", text)
        self.assertIn("at {}:".format(os.path.abspath(__file__)), text)
        self.assertIn("traceback:", text)

    def test_format_exception_without_traceback(self):
        try:
            raise ValueError("short")
        except ValueError as exc:
            text = pfm.format_exception(exc, mod_id="m", phase="p",
                                        include_traceback=False)
        self.assertNotIn("traceback:", text)
        self.assertIn("ValueError: short", text)

    def test_entrypoint_error_chains_the_cause(self):
        with self.assertRaises(pfm.EntrypointError) as ctx:
            pfm._load_entrypoint("tests.support.broken.entry:Broken", "initialize")
        self.assertIsInstance(ctx.exception.__cause__, ValueError)
        self.assertIn("caused by ValueError",
                      pfm.format_exception(ctx.exception, mod_id="mod_a",
                                           phase="initialize",
                                           include_traceback=False))

    def test_handler_error_reaches_the_game_log_through_the_bridge(self):
        @pfm.event("server_start", mod_id="mod_a")
        def handler(event):
            raise KeyError("missing")

        report = pfm.dispatch("server_start")
        self.assertFalse(report.ok)
        errors = self.bridge.messages("error")
        self.assertEqual(len(errors), 1)
        self.assertIn("KeyError", errors[0])
        self.assertIn("mod_a", errors[0])
        self.assertIn(os.path.join("tests", "test_traceback.py"), errors[0])

    def test_error_mentions_the_mod_id_of_the_owner(self):
        pfm._bootstrap("mod_b", "server", None)

        @pfm.event("server_start", mod_id="mod_b")
        def handler(event):
            raise RuntimeError("from b")

        report = pfm.dispatch("server_start", mod_id="mod_b")
        self.assertEqual(report.mod_id, "mod_b")
        self.assertIn("mod_b", report.errors[0])


if __name__ == "__main__":
    unittest.main()
