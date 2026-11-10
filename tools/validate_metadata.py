#!/usr/bin/env python3
"""Static validation of every mod metadata file in this repository.

This is a real check, not a lint of style: it verifies the wiring that a JVM build would
otherwise only discover at start-up.

* every ``fabric.mod.json`` parses, has the required fields and a valid ``environment``;
* every ``neoforge.mods.toml`` parses and declares a known ``modLoader``;
* every entry point (``package.module:attribute``) resolves to a Python file that exists in
  the project and defines that attribute (checked with ``ast``, so no import happens);
* every declared ``modules``/``python_root`` directory exists;
* every dependency on a Python-for-Minecraft component names a real component id;
* the language adapter class named by the Fabric core and by the NeoForge service file
  exists as a source file in this repository.

Run it with::

    python3 tools/validate_metadata.py
"""

from __future__ import annotations

import ast
import json
import os
import re
import sys
import tomllib
from typing import Dict, Iterable, List, Optional, Tuple

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

COMPONENT_IDS = {
    "pythonforminecraft_core",
    "pythonforminecraft",
    "pythonforminecraft_server",
}
FABRIC_ADAPTER_CLASS = "io.github.goshadows.pythonforminecraft.fabric.PythonLanguageAdapter"
NEOFORGE_LOADER_CLASS = "io.github.goshadows.pythonforminecraft.neoforge.PythonNeoForgeLoader"
ENTRY_RE = re.compile(r"^[A-Za-z_][\w.]*:[A-Za-z_]\w*$")

CORE_JAVA_ROOTS = [
    os.path.join(REPO, "core", "src", "main", "java"),
    os.path.join(REPO, "loader-adapters"),
]


class Report:
    def __init__(self) -> None:
        self.errors: List[str] = []
        self.checked = 0

    def error(self, message: str) -> None:
        self.errors.append(message)

    def ok(self, message: str) -> None:
        self.checked += 1
        print("  ok   " + message)


def find(pattern: str) -> List[str]:
    matches = []
    for root, dirs, files in os.walk(REPO):
        dirs[:] = [d for d in dirs if d not in {".git", "__pycache__", "build", ".gradle"}]
        for name in files:
            path = os.path.join(root, name)
            if path.endswith(pattern):
                matches.append(os.path.relpath(path, REPO))
    return sorted(matches)


def python_root_for(rel_path: str) -> Optional[str]:
    """The ``python/`` directory that belongs to the project of *rel_path*."""
    directory = os.path.dirname(os.path.join(REPO, rel_path))
    while directory != os.path.dirname(directory):
        candidate = os.path.join(directory, "python")
        if os.path.isdir(candidate):
            return candidate
        parent = os.path.dirname(directory)
        if parent == directory:
            break
        directory = parent
    return None


def module_file(python_root: str, module: str) -> Optional[str]:
    relative = module.replace(".", os.sep)
    for candidate in (os.path.join(python_root, relative + ".py"),
                      os.path.join(python_root, relative, "__init__.py")):
        if os.path.isfile(candidate):
            return candidate
    return None


def defines(path: str, attribute: str) -> bool:
    with open(path, encoding="utf-8") as handle:
        tree = ast.parse(handle.read(), filename=path)
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if node.name == attribute:
                return True
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == attribute:
                    return True
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            if node.target.id == attribute:
                return True
    return False


def check_entrypoint(report: Report, where: str, spec: str, python_root: Optional[str],
                     search_paths: Iterable[str]) -> None:
    if not ENTRY_RE.match(spec):
        report.error("%s: entry point %r is not 'package.module:attribute'" % (where, spec))
        return
    module, _, attribute = spec.partition(":")
    for root in search_paths:
        if root is None:
            continue
        path = module_file(root, module)
        if path is not None:
            if defines(path, attribute):
                report.ok("%s -> %s:%s (%s)" % (
                    where, module, attribute, os.path.relpath(path, REPO)))
            else:
                report.error("%s: %s does not define %r" % (
                    where, os.path.relpath(path, REPO), attribute))
            return
    report.error("%s: module %r not found in %s" % (where, module,
                 ", ".join(os.path.relpath(p, REPO) for p in search_paths if p)))


def java_class_exists(fqcn: str) -> bool:
    relative = fqcn.replace(".", os.sep) + ".java"
    for root_dir, _, files in _walk_java():
        for name in files:
            if name.endswith(".java"):
                full = os.path.join(root_dir, name)
                if full.endswith(relative):
                    return True
    return False


def _walk_java():
    for root in CORE_JAVA_ROOTS:
        if not os.path.isdir(root):
            continue
        for dirpath, dirs, files in os.walk(root):
            dirs[:] = [d for d in dirs if d != "__pycache__"]
            yield dirpath, dirs, files


def check_fabric(report: Report, rel_path: str) -> None:
    with open(os.path.join(REPO, rel_path), encoding="utf-8") as handle:
        text = handle.read()
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exception:
        report.error("%s: invalid JSON (%s)" % (rel_path, exception))
        return
    for field in ("schemaVersion", "id", "version", "name", "environment", "license"):
        if field not in data:
            report.error("%s: missing required field %r" % (rel_path, field))
    if data.get("schemaVersion") != 1:
        report.error("%s: schemaVersion must be 1, got %r" % (rel_path,
                                                              data.get("schemaVersion")))
    environment = data.get("environment")
    if environment not in ("client", "server", "*"):
        report.error("%s: invalid environment %r" % (rel_path, environment))
    mod_id = data.get("id", "?")
    if not re.match(r"^[a-z0-9][a-z0-9_-]{0,62}$", str(mod_id)):
        report.error("%s: invalid mod id %r" % (rel_path, mod_id))

    depends = data.get("depends", {})
    for dependency in depends:
        if dependency.startswith("pythonforminecraft") and dependency not in COMPONENT_IDS:
            report.error("%s: depends on unknown component %r" % (rel_path, dependency))
    if mod_id in COMPONENT_IDS and mod_id != "pythonforminecraft_core":
        if "pythonforminecraft_core" not in depends:
            report.error("%s: must depend on pythonforminecraft_core" % rel_path)

    adapters = data.get("languageAdapters", {})
    if mod_id == "pythonforminecraft_core":
        if adapters.get("python") != FABRIC_ADAPTER_CLASS:
            report.error("%s: core must declare languageAdapters.python = %s"
                         % (rel_path, FABRIC_ADAPTER_CLASS))
        else:
            if java_class_exists(FABRIC_ADAPTER_CLASS):
                report.ok("%s: language adapter %s exists" % (rel_path, FABRIC_ADAPTER_CLASS))
            else:
                report.error("%s: language adapter class %s not found in the repository"
                             % (rel_path, FABRIC_ADAPTER_CLASS))
        if data.get("entrypoints"):
            report.error("%s: the core must not declare entrypoints" % rel_path)
        if environment != "*":
            report.error("%s: the core must have environment '*' so it loads on both sides"
                         % rel_path)
    elif adapters:
        report.error("%s: only the core may declare languageAdapters" % rel_path)

    custom = (data.get("custom") or {}).get("pythonforminecraft")
    roots = []
    project_python = python_root_for(rel_path)
    if project_python:
        roots.append(project_python)
    for entry_key, entries in (data.get("entrypoints") or {}).items():
        for entry in entries:
            if isinstance(entry, dict) and entry.get("adapter") == "python":
                check_entrypoint(report, "%s [%s]" % (rel_path, entry_key),
                                 entry.get("value", ""), project_python, roots)
            elif isinstance(entry, str) and mod_id in COMPONENT_IDS:
                if not java_class_exists(entry):
                    report.error("%s: Java entry point %s not found" % (rel_path, entry))
                else:
                    report.ok("%s: Java entry point %s exists" % (rel_path, entry))
    if custom:
        python_root = custom.get("python_root", "python")
        for module in custom.get("modules", []):
            if project_python is None:
                report.error("%s: declares modules but has no python/ directory"
                             % rel_path)
            elif module_file(project_python, module) is None:
                report.error("%s: declared module %r has no source under %s"
                             % (rel_path, module,
                                os.path.relpath(project_python, REPO)))
            else:
                report.ok("%s: module %s found" % (rel_path, module))
        for vendor in custom.get("vendor", []):
            if project_python is None:
                continue
            candidate = os.path.normpath(os.path.join(project_python, "..", vendor))
            if os.path.isdir(candidate):
                report.ok("%s: vendor dir %s exists" % (rel_path, vendor))
            else:
                report.error("%s: vendor dir %s missing (%s)" % (rel_path, vendor,
                                                                 candidate))
        if python_root != "python":
            report.error("%s: unsupported python_root %r (expected 'python')"
                         % (rel_path, python_root))


def check_neoforge(report: Report, rel_path: str) -> None:
    with open(os.path.join(REPO, rel_path), "rb") as handle:
        raw = handle.read()
    text = raw.decode("utf-8")
    # ${version} is expanded by Gradle at build time; tomllib needs a literal.
    text = text.replace("${version}", "0.0.0-PLACEHOLDER")
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError as exception:
        report.error("%s: invalid TOML (%s)" % (rel_path, exception))
        return
    loader = data.get("modLoader")
    if loader not in ("javafml", "pythonforminecraft"):
        report.error("%s: unexpected modLoader %r" % (rel_path, loader))
    if "license" not in data:
        report.error("%s: missing license" % rel_path)
    mods = data.get("mods", [])
    if not mods:
        report.error("%s: no [[mods]] entry" % rel_path)
    project_python = python_root_for(rel_path)
    properties = data.get("modproperties", {})
    for mod in mods:
        mod_id = mod.get("modId", "?")
        if not re.match(r"^[a-z][a-z0-9_]{0,62}$", str(mod_id)):
            report.error("%s: invalid modId %r" % (rel_path, mod_id))
        for field in ("version", "displayName", "description"):
            if field not in mod:
                report.error("%s: [[mods]] %s missing %r" % (rel_path, mod_id, field))
        for dependency in data.get("dependencies", {}).get(mod_id, []):
            target = dependency.get("modId")
            if (str(target).startswith("pythonforminecraft")
                    and target not in COMPONENT_IDS):
                report.error("%s: depends on unknown component %r" % (rel_path, target))
        if loader == "pythonforminecraft":
            mod_properties = properties.get(mod_id, {})
            if not mod_properties:
                report.error("%s: modLoader=pythonforminecraft needs "
                             "[modproperties.%s]" % (rel_path, mod_id))
            found = False
            for key in ("pyfm_main", "pyfm_client", "pyfm_server"):
                if key in mod_properties:
                    found = True
                    check_entrypoint(report, "%s %s" % (rel_path, key),
                                     str(mod_properties[key]), project_python,
                                     [project_python])
            if not found:
                report.error("%s: no pyfm_main/pyfm_client/pyfm_server entry point"
                             % rel_path)
            for module in mod_properties.get("modules", []):
                if project_python is None:
                    report.error("%s: declares modules but has no python/ directory"
                                 % rel_path)
                elif module_file(project_python, module) is None:
                    report.error("%s: declared module %r has no source" % (rel_path, module))
                else:
                    report.ok("%s: module %s found" % (rel_path, module))


def check_neoforge_service(report: Report, rel_path: str) -> None:
    with open(os.path.join(REPO, rel_path), encoding="utf-8") as handle:
        classes = [line.strip() for line in handle if line.strip() and
                   not line.startswith("#")]
    if classes != [NEOFORGE_LOADER_CLASS]:
        report.error("%s: expected exactly %s, got %s" % (rel_path, NEOFORGE_LOADER_CLASS,
                                                          classes))
        return
    if java_class_exists(NEOFORGE_LOADER_CLASS):
        report.ok("%s: %s exists" % (rel_path, NEOFORGE_LOADER_CLASS))
    else:
        report.error("%s: class %s not found in the repository"
                     % (rel_path, NEOFORGE_LOADER_CLASS))


def self_test() -> int:
    """Proves the validator actually fails on broken metadata.

    Builds a throw-away tree with four deliberately wrong things and requires the checks to
    reject every one of them. Without this the tool could pass on anything.
    """
    import tempfile

    global REPO  # restored in the finally block
    original = REPO
    cases = [
        ("broken-adapter", "fabric.mod.json", json.dumps({
            "schemaVersion": 1, "id": "x", "version": "1", "name": "n",
            "environment": "both", "license": "Apache-2.0",
            "languageAdapters": {"python": "io.github.goshadows.Missing"},
        }), check_fabric),
        ("broken-entrypoint", "fabric.mod.json", json.dumps({
            "schemaVersion": 1, "id": "pyhello_client", "version": "1", "name": "n",
            "environment": "client", "license": "Apache-2.0",
            "entrypoints": {"client": [{"adapter": "python",
                                        "value": "pyhello_client.entry:DoesNotExist"}]},
            "depends": {"pythonforminecraft_nope": ">=1.0.0"},
        }), check_fabric),
        ("broken-neoforge", "neoforge.mods.toml",
         "modLoader = \"pythonlang\"\n"
         "license = \"Apache-2.0\"\n"
         "[[mods]]\n"
         "modId = \"pyhello_common\"\n"
         "version = \"1\"\n"
         "displayName = \"n\"\n"
         "description = \"d\"\n"
         "[modproperties.pyhello_common]\n"
         "pyfm_main = \"pyhello_common.entry:Missing\"\n"
         "modules = [\"no_such_module\"]\n", check_neoforge),
        ("bad-json", "fabric.mod.json", "{\"id\": \"x\",", check_fabric),
    ]
    try:
        with tempfile.TemporaryDirectory() as tmp:
            REPO = tmp
            rejected = 0
            for name, filename, content, checker in cases:
                path = os.path.join(tmp, "proj", name, "src", "main", "resources",
                                    "META-INF" if filename == "neoforge.mods.toml" else ".")
                if filename == "neoforge.mods.toml":
                    path = os.path.join(tmp, "proj", name, "src", "main", "resources",
                                        "META-INF", filename)
                else:
                    path = os.path.join(tmp, "proj", name, "src", "main", "resources",
                                        filename)
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, "w", encoding="utf-8") as handle:
                    handle.write(content)
                report = Report()
                checker(report, os.path.relpath(path, tmp))
                if report.errors:
                    rejected += 1
                    print("  ok   rejected %s (%d problem(s), first: %s)"
                          % (name, len(report.errors), report.errors[0]))
                else:
                    print("  FAIL validator accepted the broken %s case" % name)
            if rejected != len(cases):
                print("SELF-TEST FAILED: %d/%d broken cases rejected"
                      % (rejected, len(cases)))
                return 1
            print("SELF-TEST PASSED: %d/%d broken cases rejected" % (rejected, len(cases)))
            return 0
    finally:
        REPO = original


def main() -> int:
    if "--self-test" in sys.argv:
        return self_test()
    report = Report()
    fabric = find("fabric.mod.json")
    neoforge = find("neoforge.mods.toml")
    services = [p for p in find("IModLanguageLoader")
                if p.endswith("net.neoforged.neoforgespi.language.IModLanguageLoader")]
    print("fabric.mod.json files: %d" % len(fabric))
    for path in fabric:
        print("* " + path)
        check_fabric(report, path)
    print("neoforge.mods.toml files: %d" % len(neoforge))
    for path in neoforge:
        print("* " + path)
        check_neoforge(report, path)
    print("IModLanguageLoader service files: %d" % len(services))
    for path in services:
        print("* " + path)
        check_neoforge_service(report, path)
    print()
    if report.errors:
        print("FAILED: %d problem(s)" % len(report.errors))
        for error in report.errors:
            print("  - " + error)
        return 1
    print("PASSED: %d checks, no problems" % report.checked)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
