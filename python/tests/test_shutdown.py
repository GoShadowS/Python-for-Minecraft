import unittest

import pfm

from .base import PfmTestCase


class ShutdownTests(PfmTestCase):
    def test_shutdown_clears_handlers_commands_and_entrypoints(self):
        pfm.autodiscover("tests.support.mod_a")
        self.assertGreater(pfm.runtime().handler_count(), 0)
        pfm._shutdown("mod_a")
        self.assertEqual(pfm.all_runtimes(), ())

    def test_closed_runtime_refuses_new_handlers(self):
        rt = pfm.runtime()
        rt.close()
        with self.assertRaises(pfm.HandlerError) as ctx:
            rt.add_handler(pfm.Handler("server_start", lambda e: None))
        self.assertIn("already shut down", str(ctx.exception))

    def test_registration_after_shutdown_fails_loudly(self):
        pfm._shutdown("mod_a")
        with self.assertRaises(pfm.HandlerError):
            pfm.register_handler("server_start", lambda e: None)

    def test_dispatch_after_shutdown_fails_loudly(self):
        pfm._shutdown("mod_a")
        with self.assertRaises(pfm.HandlerError):
            pfm.dispatch("server_start")

    def test_shutdown_all(self):
        pfm._bootstrap("mod_b", "server", None)
        pfm._shutdown()
        self.assertEqual(pfm.all_runtimes(), ())
        self.assertIsNone(pfm.current_mod_id())

    def test_bootstrapping_again_after_shutdown_works(self):
        pfm._shutdown("mod_a")
        pfm._bootstrap("mod_a", "client", None)
        self.assertEqual(pfm.side(), pfm.Side.CLIENT)
        self.assertTrue(pfm.is_client())
        self.assertFalse(pfm.is_server())


if __name__ == "__main__":
    unittest.main()
