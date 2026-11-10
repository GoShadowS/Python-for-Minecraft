import unittest

import pfm
from pfm import _bridge

from .base import PfmTestCase


class BridgeTests(PfmTestCase):
    def test_bridge_is_installed_by_bootstrap(self):
        self.assertTrue(_bridge.is_installed())
        self.assertIs(_bridge.bridge(), self.bridge)

    def test_missing_bridge_raises(self):
        _bridge.reset()
        with self.assertRaises(pfm.BridgeError) as ctx:
            _bridge.bridge()
        self.assertIn("bridge is not installed", str(ctx.exception))

    def test_logging_goes_through_the_bridge(self):
        pfm.log.info("hello")
        pfm.log.warn("careful")
        pfm.log.error("broken")
        self.assertIn("hello", self.bridge.messages("info"))
        self.assertIn("careful", self.bridge.messages("warn"))
        self.assertIn("broken", self.bridge.messages("error"))

    def test_java_import_class(self):
        cls = pfm.java.import_class("net.minecraft.server.MinecraftServer")
        self.assertEqual(cls.getName(), "net.minecraft.server.MinecraftServer")
        self.assertTrue(pfm.java.is_available())

    def test_java_import_class_uses_bridge_registry(self):
        sentinel = object()
        self.bridge.classes["com.example.Thing"] = sentinel
        self.assertIs(pfm.java.import_class("com.example.Thing"), sentinel)

    def test_mc_handles_are_lazy(self):
        self.assertIsNone(pfm.mc.server)
        server = object()
        self.bridge.handles["server"] = server
        self.assertIs(pfm.mc.server, server)
        self.assertIsNone(pfm.mc.client)

    def test_logging_without_a_bridge_falls_back_to_stdlib(self):
        _bridge.reset()
        with self.assertLogs("pythonforminecraft", level="INFO") as captured:
            pfm.get_logger("mod_a").info("no bridge here")
        self.assertTrue(any("no bridge here" in line for line in captured.output))


if __name__ == "__main__":
    unittest.main()
