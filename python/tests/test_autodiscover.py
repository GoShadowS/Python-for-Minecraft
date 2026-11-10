import unittest

import pfm

from .base import PfmTestCase


class AutodiscoverTests(PfmTestCase):
    def test_autodiscover_imports_submodules_and_registers(self):
        loaded = pfm.autodiscover("tests.support.mod_a")
        self.assertIn("tests.support.mod_a", loaded)
        self.assertIn("tests.support.mod_a.entry", loaded)
        self.assertIn("tests.support.mod_a.handlers", loaded)
        self.assertEqual(pfm.runtime().handler_count("server_start"), 2)
        self.assertIn("pyhello", pfm.runtime().commands)

    def test_autodiscover_is_tracked_on_the_runtime(self):
        pfm.autodiscover("tests.support.mod_a")
        self.assertIn("tests.support.mod_a.handlers", pfm.runtime().loaded_modules)

    def test_autodiscover_twice_does_not_duplicate(self):
        pfm.autodiscover("tests.support.mod_a")
        pfm.autodiscover("tests.support.mod_a")
        self.assertEqual(pfm.runtime().handler_count("server_start"), 2)

    def test_autodiscover_of_another_package(self):
        loaded = pfm.autodiscover("tests.support.mod_b")
        self.assertIn("tests.support.mod_b", loaded)
        self.assertIn("tests.support.mod_b.handlers", loaded)
        self.assertEqual(pfm.runtime().handler_count("server_start"), 1)


if __name__ == "__main__":
    unittest.main()
