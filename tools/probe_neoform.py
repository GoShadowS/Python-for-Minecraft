#!/usr/bin/env python3
"""Report what tooling versions actually exist for a NeoForge target, and whether that
target's NeoForm config uses functions the resolved NeoFormRuntime understands.

Run 42986520306 failed neoforge-26.3 with, in order:

    Failed to parse MC version from NeoForge version 26.3.0.100. Using capabilities of
    latest known Minecraft version with Minecraft version 1.21.4.
    ...
    java.lang.IllegalArgumentException: Function for step preProcessJar has invalid tool: null
        at net.neoforged.neoform.runtime.engine.NeoFormEngine.applyFunctionToNode

The first line is ModDevGradle's MinecraftVersionList not knowing this Minecraft version;
the second is NeoFormRuntime failing to map a function name from the NeoForm config to a
tool. This script gathers the primary evidence: which ModDevGradle versions are published,
which NeoForm version the NeoForge userdev jar asks for, and which function names that
config uses.

Usage: tools/probe_neoform.py <neoforge-version>
"""

from __future__ import annotations

import io
import json
import re
import sys
import urllib.request
import zipfile

BASES = {
    "releases": "https://maven.neoforged.net/releases",
    "snapshots": "https://maven.neoforged.net/snapshots",
}


def get(url: str, binary: bool = False, timeout: int = 60):
    req = urllib.request.Request(url, headers={"User-Agent": "python-for-minecraft-ci"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read()
            return resp.status, body if binary else body.decode("utf-8", "replace")
    except Exception as exc:  # noqa: BLE001 - a probe must report, never raise
        return None, f"{type(exc).__name__}: {exc}"


def versions(marker_path: str) -> list[str]:
    out: list[str] = []
    for name, base in BASES.items():
        status, body = get(f"{base}/{marker_path}/maven-metadata.xml")
        if status != 200:
            print(f"  {name}: HTTP {status} {body if status is None else ''}".rstrip())
            continue
        found = re.findall(r"<version>([^<]+)</version>", body)
        print(f"  {name}: {len(found)} versions, newest {found[-6:] if found else found}")
        out.extend(found)
    return out


def main() -> int:
    neoforge = sys.argv[1] if len(sys.argv) > 1 else "26.3.0.102"

    print("## ModDevGradle plugin marker net.neoforged.moddev")
    mdg = versions("net/neoforged/moddev/net.neoforged.moddev.gradle.plugin")
    print()

    print("## NeoForge net.neoforged:neoforge")
    for name, base in BASES.items():
        status, body = get(f"{base}/net/neoforged/neoforge/maven-metadata.xml")
        if status != 200:
            print(f"  {name}: HTTP {status}")
            continue
        found = [v for v in re.findall(r"<version>([^<]+)</version>", body)
                 if v.startswith(neoforge.rsplit(".", 1)[0])]
        print(f"  {name}: matching {neoforge.rsplit('.', 1)[0]}* -> {found[-8:]}")
    print()

    print(f"## userdev jar for neoforge {neoforge}")
    userdev = (f"{BASES['releases']}/net/neoforged/neoforge/{neoforge}/"
               f"neoforge-{neoforge}-userdev.jar")
    status, blob = get(userdev, binary=True)
    if status != 200:
        print(f"  HTTP {status}: {blob}")
        return 0
    print(f"  downloaded {len(blob)} bytes")
    with zipfile.ZipFile(io.BytesIO(blob)) as zf:
        names = zf.namelist()
        print(f"  entries: {len(names)}")
        cfg_name = next((n for n in names if n.endswith("config.json")), None)
        print(f"  config entry: {cfg_name}")
        if cfg_name is None:
            return 0
        cfg = json.loads(zf.read(cfg_name))
    # 26.3.0.102's userdev config.json has no "neoform" key at all; it names "mcp" instead.
    # Run 42987535382 printed: keys: [ats, binpatcher, binpatches, features, libraries,
    # mcp, modules, patches, runs, sources, spec, testLibraries, universal].
    print(f"  keys: {sorted(cfg)}")
    print(f"  mcp section: {json.dumps(cfg.get('mcp'), sort_keys=True)}")
    print(f"  spec section: {json.dumps(cfg.get('spec'), sort_keys=True)}")
    mcp = cfg.get("mcp") or {}
    neoform = mcp.get("version") or cfg.get("neoform")
    if not neoform:
        return 0
    print()

    print(f"## NeoForm config {neoform}")
    for suffix in ("zip", "jar"):
        url = (f"{BASES['releases']}/net/neoforged/neoform/{neoform}/"
               f"neoform-{neoform}.{suffix}")
        status, blob = get(url, binary=True)
        if status == 200:
            print(f"  {suffix}: {len(blob)} bytes")
            break
        print(f"  {suffix}: HTTP {status}")
    else:
        return 0
    with zipfile.ZipFile(io.BytesIO(blob)) as zf:
        raw = zf.read("config.json")
    form = json.loads(raw)
    print(f"  top-level keys: {sorted(form)}")
    functions = form.get("functions") or {}
    print(f"  declared functions ({len(functions)}): {sorted(functions)}")
    used = {}
    for step in form.get("steps", {}).get("joined", []):
        fn = step.get("function")
        if fn:
            used.setdefault(fn, []).append(step.get("type"))
    print(f"  functions used by joined steps ({len(used)}):")
    for fn in sorted(used):
        tool = (functions.get(fn) or {}).get("tool")
        print(f"    {fn}: tool={tool} used_by={sorted(set(used[fn]))}")
    missing = sorted(fn for fn in used if fn not in functions)
    print(f"  used but NOT declared (would give 'invalid tool: null'): {missing}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
