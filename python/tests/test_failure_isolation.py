import unittest

import pfm

from .base import PfmTestCase


class FailureIsolationTests(PfmTestCase):
    """A Python mod that fails must be reported and must not take the others down."""

    def test_failing_entrypoint_is_reported_with_mod_and_line(self):
        pfm._bootstrap("mod_b", "server", None)
        pfm.autodiscover("tests.support.mod_b")
        pfm._bootstrap("mod_a", "server", None)

        with self.assertRaises(pfm.EntrypointError) as ctx:
            pfm._load_entrypoint("tests.support.broken.entry:Broken", "initialize")
        text = str(ctx.exception)
        self.assertIn("mod_a", text)
        self.assertIn("tests.support.broken.entry:Broken", text)
        self.assertIn("broken/entry.py", text.replace("\\", "/"))
        self.assertIn("intentional failure", text)

        # The other mod is unaffected.
        report = pfm._dispatch("server_start", None, "mod_b")
        self.assertIn("invoked=1", report)

        # The failed mod is not marked as successfully initialised.
        rt = pfm.runtime_for("mod_a")
        entrypoint = rt.entrypoints["tests.support.broken.entry:Broken"]
        self.assertNotIn("on_initialize", entrypoint.invoked)
        self.assertNotIn(("tests.support.broken.entry:Broken", "initialize"),
                         [i for i in rt.invocations
                          if "on_initialize" in entrypoint.invoked])

    def test_failing_handler_does_not_break_other_handlers_or_mods(self):
        pfm._bootstrap("mod_b", "server", None)
        pfm.autodiscover("tests.support.mod_b")
        pfm._bootstrap("mod_a", "server", None)

        @pfm.event("server_start", mod_id="mod_a")
        def broken(event):
            raise ZeroDivisionError("division by zero")

        report_a = pfm.dispatch("server_start", mod_id="mod_a")
        self.assertFalse(report_a.ok)
        self.assertIn("ZeroDivisionError", report_a.errors[0])

        report_b = pfm.dispatch("server_start", mod_id="mod_b")
        self.assertTrue(report_b.ok)
        self.assertEqual(report_b.invoked, 1)

    def test_status_snapshot_after_a_failure(self):
        with self.assertRaises(pfm.EntrypointError):
            pfm._load_entrypoint("tests.support.broken.entry:Broken", "initialize")
        status = pfm._status()
        self.assertIn("mod_a", status)
        self.assertEqual(status["mod_a"]["side"], "server")


if __name__ == "__main__":
    unittest.main()
