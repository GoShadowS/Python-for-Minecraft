import os
import sys
import tempfile
import unittest

import pfm
from pfm import _deps

from .base import PfmTestCase


class DependencyPathTests(PfmTestCase):
    def test_vendor_directory_is_added_to_sys_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            added = pfm._setup_paths([tmp])
            self.assertEqual(added, [os.path.abspath(tmp)])
            self.assertEqual(sys.path[0], os.path.abspath(tmp))
            _deps.remove_paths([tmp])
            self.assertNotIn(os.path.abspath(tmp), sys.path)

    def test_missing_directories_are_skipped(self):
        added = pfm._setup_paths(["/definitely/not/here"])
        self.assertEqual(added, [])

    def test_adding_twice_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            first = pfm._setup_paths([tmp])
            second = pfm._setup_paths([tmp])
            self.assertEqual(len(first), 1)
            self.assertEqual(second, [])
            self.assertEqual(sys.path.count(os.path.abspath(tmp)), 1)
            _deps.remove_paths([tmp])

    def test_a_vendored_package_becomes_importable(self):
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(tmp, "pyfm_vendor_probe.py"), "w") as handle:
                handle.write("VALUE = 'vendored'\n")
            pfm._setup_paths([tmp])
            try:
                import pyfm_vendor_probe  # noqa: PLC0415

                self.assertEqual(pyfm_vendor_probe.VALUE, "vendored")
            finally:
                sys.modules.pop("pyfm_vendor_probe", None)
                _deps.remove_paths([tmp])

    def test_string_input_is_accepted(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(len(pfm._setup_paths(tmp)), 1)
            _deps.remove_paths([tmp])


if __name__ == "__main__":
    unittest.main()
