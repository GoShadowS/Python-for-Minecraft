#!/usr/bin/env python3
"""Vendor pure-Python dependencies into a Python mod, reproducibly.

Nothing is downloaded while the game runs.  At build time this script resolves a pinned,
hash-locked requirements file, downloads the wheels, verifies their sha256, refuses
anything that is not a pure-Python wheel, unpacks the wheels into a vendor directory that
is shipped inside the mod jar, and writes ``VENDOR.lock.json`` next to them.

Usage::

    python3 tools/vendor_deps.py \\
        --requirements examples/pyhello-common/requirements.txt \\
        --out examples/pyhello-common/python/vendor

    # offline, verifies the checked-in vendor tree against the lock file
    python3 tools/vendor_deps.py --check --out examples/pyhello-common/python/vendor

The requirements file must be fully pinned and transitively closed (``--no-deps``
semantics) and every line must carry at least one ``--hash=sha256:...``, exactly like a
``pip install --require-hashes`` input file.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from typing import Dict, List, NamedTuple, Optional

WHEEL_RE = re.compile(
    r"^(?P<name>[A-Za-z0-9_.-]+)-(?P<version>[^-]+)"
    r"(-(?P<build>\d[^-]*))?-(?P<pytag>[^-]+)-(?P<abitag>[^-]+)-(?P<plattag>[^-]+)\.whl$")

BINARY_SUFFIXES = (".so", ".pyd", ".dylib", ".dll")

LOCK_NAME = "VENDOR.lock.json"


class Requirement(NamedTuple):
    spec: str
    hashes: List[str]


class Vendored(NamedTuple):
    name: str
    version: str
    wheel: str
    sha256: str
    license_file: Optional[str]


# ------------------------------------------------------------------ pure, testable parts
def _logical_lines(text: str) -> List[str]:
    """Join backslash-continued lines the way pip does."""
    joined: List[str] = []
    pending = ""
    for raw in text.splitlines():
        line = raw.strip()
        if line.endswith("\\"):
            pending += line[:-1].strip() + " "
            continue
        pending += line
        joined.append(pending.strip())
        pending = ""
    if pending:
        joined.append(pending.strip())
    return joined


HASH_TOKEN_RE = re.compile(r"--hash=(sha256:[0-9a-fA-F]{64})")
ANY_HASH_RE = re.compile(r"--hash=([A-Za-z0-9]+):")


def parse_requirements(text: str) -> List[Requirement]:
    """Parse a pip ``--require-hashes`` style requirements file.

    Every requirement must be fully pinned (``==``) and carry at least one
    ``--hash=sha256:...``, either on the same logical line or on a continued one.
    """
    requirements: List[Requirement] = []
    for line in _logical_lines(text):
        if not line or line.startswith("#"):
            continue
        for algorithm in ANY_HASH_RE.findall(line):
            if algorithm != "sha256":
                raise ValueError("only sha256 hashes are supported, got {!r}"
                                 .format(algorithm))
        hashes = [m.split(":", 1)[1] for m in HASH_TOKEN_RE.findall(line)]
        spec = HASH_TOKEN_RE.sub("", line).strip()
        if "--hash=" in spec:
            raise ValueError("malformed --hash entry in {!r}; expected "
                             "--hash=sha256:<64 hex characters>".format(line))
        if not spec:
            raise ValueError("a --hash= entry without a requirement: {!r}".format(line))
        if spec.startswith("-"):
            raise ValueError("unsupported requirements directive {!r}".format(spec))
        if not re.match(r"^[A-Za-z0-9_.\-]+==[^ ;]+$", spec):
            raise ValueError("requirement {!r} must be fully pinned with =="
                             .format(spec))
        if not hashes:
            raise ValueError(
                "requirement {!r} has no --hash=sha256:... entry; vendoring must be "
                "reproducible".format(spec))
        if any(not re.match(r"^[0-9a-f]{64}$", h) for h in hashes):
            raise ValueError("malformed sha256 hash in {!r}".format(line))
        requirements.append(Requirement(spec, sorted(set(hashes))))
    if not requirements:
        raise ValueError("no requirements found")
    return requirements


def sha256_file(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def wheel_is_pure_python(filename: str, path: str) -> bool:
    """True when the wheel is a ``py*-none-any`` wheel with no binary payload."""
    match = WHEEL_RE.match(os.path.basename(filename))
    if match is None:
        return False
    if match.group("abitag") != "none" or match.group("plattag") != "any":
        return False
    with zipfile.ZipFile(path) as archive:
        for name in archive.namelist():
            if name.lower().endswith(BINARY_SUFFIXES):
                return False
    return True


def read_lock(vendor_dir: str) -> Dict:
    with open(os.path.join(vendor_dir, LOCK_NAME), encoding="utf-8") as handle:
        return json.load(handle)


# ------------------------------------------------------------------------- build actions
def download(spec: str, cache: str) -> str:
    os.makedirs(cache, exist_ok=True)
    cmd = [sys.executable, "-m", "pip", "download", "--no-deps", "--only-binary=:all:",
           "--dest", cache, spec]
    subprocess.run(cmd, check=True)
    stem = re.split(r"==|>=|<=|~=|!=|<|>", spec)[0].replace("-", "_").replace(".", "_")
    matches = [f for f in sorted(os.listdir(cache))
               if f.lower().startswith(stem.lower()) and f.endswith(".whl")]
    if len(matches) != 1:
        raise RuntimeError("expected exactly one wheel for {!r} in {}, found {}".format(
            spec, cache, matches))
    return os.path.join(cache, matches[0])


def unpack(wheel: str, vendor_dir: str) -> Optional[str]:
    """Unpack a wheel into *vendor_dir*; return the license file name if present."""
    license_file: Optional[str] = None
    with zipfile.ZipFile(wheel) as archive:
        archive.extractall(vendor_dir)
        for name in archive.namelist():
            if re.search(r"\.dist-info/(LICEN[CS]E|COPYING)", name, re.IGNORECASE):
                license_file = name
    return license_file


def vendor(requirements: List[Requirement], out: str, cache: str) -> List[Vendored]:
    os.makedirs(out, exist_ok=True)
    vendored: List[Vendored] = []
    for requirement in requirements:
        wheel = download(requirement.spec, cache)
        digest = sha256_file(wheel)
        if digest not in requirement.hashes:
            raise RuntimeError(
                "hash mismatch for {}: expected one of {}, got {}".format(
                    requirement.spec, requirement.hashes, digest))
        if not wheel_is_pure_python(wheel, wheel):
            raise RuntimeError(
                "{} is not a pure-Python wheel; Python-for-Minecraft only vendors "
                "py*-none-any wheels".format(os.path.basename(wheel)))
        license_file = unpack(wheel, out)
        match = WHEEL_RE.match(os.path.basename(wheel))
        vendored.append(Vendored(match.group("name"), match.group("version"),
                                 os.path.basename(wheel), digest, license_file))
    return vendored


def write_lock(out: str, vendored: List[Vendored], requirements: List[Requirement]) -> str:
    lock = {
        "lock_version": 1,
        "generator": "tools/vendor_deps.py",
        "note": "Generated. Do not edit. Re-run tools/vendor_deps.py to update.",
        "packages": [
            {
                "name": item.name,
                "version": item.version,
                "wheel": item.wheel,
                "sha256": item.sha256,
                "license_file": item.license_file,
                "requirement": next((r.spec for r in requirements
                                     if r.spec.split("==")[0].replace("-", "_")
                                     .lower() == item.name.replace("-", "_").lower()),
                                    None),
            }
            for item in vendored
        ],
    }
    path = os.path.join(out, LOCK_NAME)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(lock, handle, indent=2, sort_keys=True)
        handle.write("\n")
    return path


def check(out: str) -> int:
    """Offline verification of a checked-in vendor tree.  Returns a process exit code."""
    lock_path = os.path.join(out, LOCK_NAME)
    if not os.path.exists(lock_path):
        print("FAIL: {} not found".format(lock_path))
        return 1
    lock = read_lock(out)
    failures = 0
    for package in lock["packages"]:
        missing = [entry for entry in (package["license_file"],)
                   if entry and not os.path.exists(os.path.join(out, entry))]
        top_level = os.path.join(out, package["name"].replace("-", "_"))
        if not (os.path.isdir(top_level)
                or any(os.path.isdir(os.path.join(out, name))
                       for name in os.listdir(out)
                       if name.lower().startswith(package["name"].lower()[:4]))):
            missing.append("<package directory>")
        if missing:
            print("FAIL: {} {} missing {}".format(package["name"], package["version"],
                                                  missing))
            failures += 1
        else:
            print("ok: {} {} (wheel sha256 {})".format(package["name"], package["version"],
                                                       package["sha256"]))
    return 1 if failures else 0


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--requirements")
    parser.add_argument("--out", required=True)
    parser.add_argument("--cache", default=os.path.join(tempfile.gettempdir(),
                                                        "pyfm-wheel-cache"))
    parser.add_argument("--clean", action="store_true",
                        help="empty the vendor directory first")
    parser.add_argument("--check", action="store_true",
                        help="verify an existing vendor tree offline and exit")
    args = parser.parse_args(argv)

    if args.check:
        return check(args.out)
    if not args.requirements:
        parser.error("--requirements is required unless --check is given")

    with open(args.requirements, encoding="utf-8") as handle:
        requirements = parse_requirements(handle.read())

    out = os.path.abspath(args.out)
    if args.clean and os.path.isdir(out):
        shutil.rmtree(out)
    vendored = vendor(requirements, out, args.cache)
    lock_path = write_lock(out, vendored, requirements)
    print("vendored {} package(s) into {}".format(len(vendored), out))
    for item in vendored:
        print("  - {} {} (sha256 {})".format(item.name, item.version, item.sha256))
    print("lock file: {}".format(lock_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
