import unittest

import pfm

from .base import PfmTestCase


class IsolationTests(PfmTestCase):
    def setUp(self):
        super().setUp()
        # A second mod, sharing this process the way "shared" isolation mode would.
        pfm._bootstrap("mod_b", "server", None)
        pfm.autodiscover("tests.support.mod_b")
        pfm._bootstrap("mod_a", "server", None)
        pfm.autodiscover("tests.support.mod_a")

    def test_handlers_do_not_leak_between_mods(self):
        a = pfm.runtime_for("mod_a")
        b = pfm.runtime_for("mod_b")
        self.assertEqual(a.handler_count("server_start"), 2)   # normal + high priority
        self.assertEqual(b.handler_count("server_start"), 1)
        self.assertEqual({h.module for h in a.handlers["server_start"]},
                         {"tests.support.mod_a.handlers"})
        self.assertEqual({h.module for h in b.handlers["server_start"]},
                         {"tests.support.mod_b.handlers"})

    def test_dispatch_only_touches_the_target_mod(self):
        from .support.mod_a import handlers as a_handlers
        from .support.mod_b import handlers as b_handlers

        a_handlers.reset()
        b_handlers.reset()
        report = pfm._dispatch("server_start", None, "mod_a")
        self.assertIn("invoked=2", report)
        self.assertEqual(len(a_handlers.CALLS), 2)
        self.assertEqual(b_handlers.CALLS, [])

        report = pfm._dispatch("server_start", None, "mod_b")
        self.assertIn("invoked=1", report)
        self.assertEqual(len(b_handlers.CALLS), 1)

    def test_same_command_name_in_two_mods_is_allowed(self):
        a = pfm.runtime_for("mod_a")
        b = pfm.runtime_for("mod_b")
        self.assertIn("pyhello", a.commands)
        self.assertIn("pyhello", b.commands)
        self.assertEqual(a.commands["pyhello"].key("mod_a"), "mod_a:pyhello")
        self.assertEqual(b.commands["pyhello"].key("mod_b"), "mod_b:pyhello")

    def test_command_key_routes_to_the_owning_mod(self):
        pfm._invoke_command("mod_b:pyhello", source="src-b")
        pfm._invoke_command("mod_a:pyhello", source="src-a")
        self.assertEqual(self.bridge.replies,
                         [("src-b", "hello from mod_b"), ("src-a", "hello from mod_a")])

    def test_duplicate_command_in_one_mod_is_rejected(self):
        with self.assertRaises(pfm.HandlerError) as ctx:
            pfm.register_command("pyhello", lambda ctx: None, mod_id="mod_a")
        self.assertIn("already registered", str(ctx.exception))

    def test_modules_are_tracked_per_mod(self):
        a = pfm.runtime_for("mod_a")
        b = pfm.runtime_for("mod_b")
        self.assertIn("tests.support.mod_a.handlers", a.loaded_modules)
        self.assertNotIn("tests.support.mod_b.handlers", a.loaded_modules)
        self.assertIn("tests.support.mod_b.handlers", b.loaded_modules)

    def test_module_globals_are_not_shared(self):
        from .support.mod_a import entry as a_entry
        from .support.mod_b import entry as b_entry

        self.assertEqual(b_entry.SECRET, "mod_b")
        self.assertFalse(hasattr(a_entry, "SECRET"))

    def test_one_mod_shutting_down_leaves_the_other_running(self):
        pfm._shutdown("mod_b")
        self.assertEqual(len(pfm.all_runtimes()), 1)
        report = pfm._dispatch("server_start", None, "mod_a")
        self.assertIn("invoked=2", report)
        with self.assertRaises(pfm.HandlerError):
            pfm.runtime_for("mod_b")

    def test_status_snapshot(self):
        status = pfm._status()
        self.assertEqual(set(status), {"mod_a", "mod_b"})
        self.assertIn("pyhello", status["mod_a"]["commands"])
        self.assertEqual(status["mod_a"]["side"], "server")


if __name__ == "__main__":
    unittest.main()
