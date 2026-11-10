import json
import os
import sys
import tempfile
import unittest
import zipfile

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(REPO, "tools"))

import vendor_deps  # noqa: E402

LOCKED = ("six==1.17.0 \\\n"
          "    --hash=sha256:4721f391ed90541fddacab5acf947aa0d3dc7d27b2e1e8eda2be8970586c3274\n")


class ParseTests(unittest.TestCase):
    def test_parses_locked_requirement(self):
        reqs = vendor_deps.parse_requirements(LOCKED)
        self.assertEqual(len(reqs), 1)
        self.assertEqual(reqs[0].spec, "six==1.17.0")
        self.assertEqual(reqs[0].hashes,
                         ["4721f391ed90541fddacab5acf947aa0d3dc7d27b2e1e8eda2be8970586c3274"])

    def test_inline_hash_on_one_line(self):
        reqs = vendor_deps.parse_requirements(
            "six==1.17.0 --hash=sha256:" + "a" * 64)
        self.assertEqual(reqs[0].hashes, ["a" * 64])

    def test_multiple_hashes(self):
        reqs = vendor_deps.parse_requirements(
            "six==1.17.0 --hash=sha256:" + "a" * 64 + " --hash=sha256:" + "b" * 64)
        self.assertEqual(reqs[0].hashes, ["a" * 64, "b" * 64])

    def test_comments_and_blank_lines_are_ignored(self):
        reqs = vendor_deps.parse_requirements("# comment\n\n" + LOCKED)
        self.assertEqual(len(reqs), 1)

    def test_rejects_bad_input(self):
        cases = {
            "six": "must be fully pinned",
            "six>=1.0 --hash=sha256:" + "a" * 64: "must be fully pinned",
            "six==1.17.0": "has no --hash",
            "--index-url http://x": "unsupported requirements directive",
            "six==1.17.0 --hash=md5:" + "a" * 32: "only sha256 hashes are supported",
            "six==1.17.0 --hash=sha256:tooshort": "malformed --hash entry",
            "": "no requirements found",
        }
        for text, expected in cases.items():
            with self.subTest(text=text):
                with self.assertRaises(ValueError) as ctx:
                    vendor_deps.parse_requirements(text)
                self.assertIn(expected, str(ctx.exception))


class PurityTests(unittest.TestCase):
    def _wheel(self, name: str, members: dict) -> str:
        path = os.path.join(tempfile.mkdtemp(), name)
        with zipfile.ZipFile(path, "w") as archive:
            for member, content in members.items():
                archive.writestr(member, content)
        return path

    def test_pure_wheel_accepted(self):
        path = self._wheel("pkg-1.0-py3-none-any.whl", {"pkg/__init__.py": ""})
        self.assertTrue(vendor_deps.wheel_is_pure_python(os.path.basename(path), path))

    def test_platform_wheel_rejected(self):
        path = self._wheel("pkg-1.0-cp311-cp311-manylinux_2_17_x86_64.whl",
                           {"pkg/__init__.py": ""})
        self.assertFalse(vendor_deps.wheel_is_pure_python(os.path.basename(path), path))

    def test_binary_payload_rejected(self):
        path = self._wheel("pkg-1.0-py3-none-any.whl",
                           {"pkg/__init__.py": "", "pkg/native.so": "\x00"})
        self.assertFalse(vendor_deps.wheel_is_pure_python(os.path.basename(path), path))


class VendoredTreeTests(unittest.TestCase):
    """The checked-in vendor tree of the example mod must be verifiable offline."""

    vendor_dir = os.path.join(REPO, "examples", "pyhello-common", "python", "vendor")

    def test_lock_file_exists_and_is_consistent(self):
        lock_path = os.path.join(self.vendor_dir, "VENDOR.lock.json")
        self.assertTrue(os.path.exists(lock_path))
        with open(lock_path, encoding="utf-8") as handle:
            lock = json.load(handle)
        self.assertEqual(lock["lock_version"], 1)
        names = {p["name"] for p in lock["packages"]}
        self.assertIn("six", names)
        for package in lock["packages"]:
            for key in ("name", "version", "wheel", "sha256", "requirement"):
                self.assertTrue(package[key], key)
            self.assertEqual(len(package["sha256"]), 64)

    def test_requirements_file_matches_the_lock(self):
        requirements = os.path.join(REPO, "examples", "pyhello-common", "requirements.txt")
        with open(requirements, encoding="utf-8") as handle:
            reqs = vendor_deps.parse_requirements(handle.read())
        lock = vendor_deps.read_lock(self.vendor_dir)
        self.assertEqual({r.spec for r in reqs},
                         {p["requirement"] for p in lock["packages"]})

    def test_offline_check_passes(self):
        self.assertEqual(vendor_deps.check(self.vendor_dir), 0)

    def test_vendored_package_is_importable_through_pfm_paths(self):
        import pfm
        from pfm import _deps

        added = pfm._setup_paths([self.vendor_dir])
        try:
            self.assertIn(os.path.abspath(self.vendor_dir), added)
            import six  # noqa: PLC0415

            self.assertTrue(hasattr(six, "moves"))
            self.assertEqual(six.__version__, "1.17.0")
        finally:
            sys.modules.pop("six", None)
            _deps.remove_paths([self.vendor_dir])


if __name__ == "__main__":
    unittest.main()
