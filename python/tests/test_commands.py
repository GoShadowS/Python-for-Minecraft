import unittest

import pfm

from .base import PfmTestCase, support


class CommandTests(PfmTestCase):
    def load_handlers(self):
        mod = support("tests.support.mod_a.handlers")
        mod.reset()
        return mod

    def test_registration_is_forwarded_to_java(self):
        self.load_handlers()
        self.assertEqual(len(self.bridge.commands), 1)
        spec = self.bridge.commands[0]
        self.assertEqual(spec["name"], "pyhello")
        self.assertEqual(spec["key"], "mod_a:pyhello")
        self.assertEqual(spec["usage"], "/pyhello")
        self.assertEqual(spec["permission"], 0)
        self.assertEqual(spec["side"], "both")

    def test_command_name_validation(self):
        for bad in ["/pyhello", "two words", ""]:
            with self.subTest(name=bad):
                with self.assertRaises(ValueError):
                    pfm.register_command(bad, lambda ctx: None, mod_id="mod_a")

    def test_command_callback_replies(self):
        self.load_handlers()
        result = pfm._invoke_command("pyhello", source="the-source", args=["a", "b"])
        self.assertEqual(result, 1)
        self.assertEqual(self.bridge.replies, [("the-source", "hello from mod_a")])

    def test_command_context_arg_helper(self):
        seen = []

        @pfm.command("args", mod_id="mod_a")
        def handler(ctx):
            seen.append((ctx.arg(0), ctx.arg(5, "fallback")))

        pfm._invoke_command("args", source="s", args=["first"])
        self.assertEqual(seen, [("first", "fallback")])

    def test_unknown_command(self):
        with self.assertRaises(pfm.HandlerError) as ctx:
            pfm._invoke_command("nope", source="s")
        self.assertIn("no such command", str(ctx.exception))

    def test_client_only_command_on_server_is_rejected(self):
        @pfm.command("clientonly", side=pfm.Side.CLIENT, mod_id="mod_a")
        def only_client(ctx):
            ctx.reply("nope")

        with self.assertRaises(pfm.HandlerError) as ctx:
            pfm._invoke_command("clientonly", source="s")
        self.assertIn("not available on the server side", str(ctx.exception))

    def test_client_only_command_runs_on_client(self):
        pfm._shutdown()
        pfm._bootstrap("mod_a", pfm.Side.CLIENT, None)
        replies = []

        @pfm.command("clientonly", side=pfm.Side.CLIENT, mod_id="mod_a")
        def only_client(ctx):
            replies.append(ctx.args)
            ctx.reply("ok")

        pfm._invoke_command("clientonly", source="s", args=["x"])
        self.assertEqual(replies, [["x"]])
        self.assertEqual(self.bridge.replies, [("s", "ok")])

    def test_command_failure_is_reported_and_propagated(self):
        @pfm.command("bad", mod_id="mod_a")
        def bad(ctx):
            raise RuntimeError("command exploded")

        with self.assertRaises(RuntimeError):
            pfm._invoke_command("bad", source="s")
        self.assertTrue(any("command exploded" in m for m in self.bridge.messages("error")))
        self.assertTrue(any("command /bad" in m for m in self.bridge.messages("error")))

    def test_permission_level_is_passed_to_java(self):
        @pfm.command("admin", permission=4, mod_id="mod_a")
        def admin(ctx):
            ctx.reply("ok")

        spec = [c for c in self.bridge.commands if c["name"] == "admin"][0]
        self.assertEqual(spec["permission"], 4)


if __name__ == "__main__":
    unittest.main()
