import unittest

import pfm

from .base import PfmTestCase, support


class EventTests(PfmTestCase):
    def load_handlers(self):
        """Import the support handlers into the current runtime and clear their log."""
        mod = support("tests.support.mod_a.handlers")
        mod.reset()
        return mod

    def test_decorator_registers_handler(self):
        @pfm.event("server_start")
        def handler(event):
            calls.append(("inline", event.name))

        calls = []
        self.assertEqual(pfm.runtime().handler_count("server_start"), 1)
        report = pfm.dispatch("server_start", {"tick": 1})
        self.assertEqual(report.invoked, 1)
        self.assertTrue(report.ok)
        self.assertEqual(calls, [("inline", "server_start")])

    def test_zero_argument_handler_is_allowed(self):
        calls = []

        @pfm.event("server_start")
        def handler():
            calls.append("noarg")

        report = pfm.dispatch("server_start")
        self.assertEqual(report.invoked, 1)
        self.assertEqual(calls, ["noarg"])

    def test_priority_order(self):
        handlers = self.load_handlers()
        pfm.autodiscover("tests.support.mod_a")
        pfm.dispatch("server_start")
        self.assertEqual([c[0] for c in handlers.CALLS],
                         ["server_start_high", "server_start"])

    def test_side_filtering_skips_client_handler_on_server(self):
        handlers = self.load_handlers()
        report = pfm.dispatch("client_tick")
        self.assertEqual(report.invoked, 0)
        self.assertEqual(report.skipped, 1)
        self.assertEqual(handlers.CALLS, [])

    def test_client_side_runtime_runs_client_handler(self):
        pfm._shutdown()
        pfm._bootstrap("mod_a", pfm.Side.CLIENT, None)
        handlers = self.load_handlers()
        report = pfm.dispatch("client_tick")
        self.assertEqual(report.invoked, 1)
        self.assertEqual(handlers.CALLS, [("client_tick", "client_tick", "mod_a")])

    def test_handler_failure_is_reported_and_does_not_stop_others(self):
        order = []

        @pfm.event("server_start", priority=5)
        def bad(event):
            order.append("bad")
            raise RuntimeError("handler exploded")

        @pfm.event("server_start")
        def good(event):
            order.append("good")

        report = pfm.dispatch("server_start")
        self.assertEqual(order, ["bad", "good"])
        self.assertEqual(report.invoked, 1)
        self.assertEqual(len(report.errors), 1)
        self.assertIn("handler exploded", report.errors[0])
        self.assertIn("event server_start", report.errors[0])
        self.assertIn("mod_a", report.errors[0])
        self.assertTrue(any("handler exploded" in m for m in self.bridge.messages("error")))

    def test_strict_dispatch_reraises(self):
        @pfm.event("server_start")
        def bad(event):
            raise RuntimeError("strict")

        with self.assertRaises(RuntimeError):
            pfm.dispatch("server_start", strict=True)

    def test_custom_event(self):
        seen = []

        @pfm.event("mod_a_custom")
        def handler(event):
            seen.append(event.data)

        pfm.fire("mod_a_custom", {"value": 42})
        self.assertEqual(seen, [{"value": 42}])

    def test_dispatch_with_explicit_mod_id(self):
        seen = []

        @pfm.event("server_start", mod_id="mod_a")
        def handler(event):
            seen.append(event.mod_id)

        summary = pfm._dispatch("server_start", None, "mod_a")
        self.assertEqual(seen, ["mod_a"])
        self.assertIn("invoked=1", summary)

    def test_event_object_carries_payload(self):
        seen = []

        @pfm.event("player_join")
        def handler(event):
            seen.append((event.name, event.data, event.mod_id))

        pfm.dispatch("player_join", {"player": "Steve"})
        self.assertEqual(seen, [("player_join", {"player": "Steve"}, "mod_a")])


if __name__ == "__main__":
    unittest.main()
