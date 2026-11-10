#!/usr/bin/env python3
"""Generates the two example Python mods for the four supported platforms.

* ``pyhello_client`` — a client-only smoke test: it must work with the client component of
  Python-for-Minecraft and without anything installed on a server.
* ``pyhello_common`` — a common/server smoke test: the same Python code runs on the client
  and on a dedicated server (with the server-capable component installed) and uses a
  vendored third-party package.

Re-generate with ``python3 tools/gen_examples.py``.
"""

from __future__ import annotations

import json
import os
import textwrap

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PYFM_VERSION = "1.0.0"

PLATFORMS = {
    "fabric-1.21.1": dict(loader="fabric", minecraft="1.21.1", java=21, gradle="9.8.2",
                          loom_plugin="net.fabricmc.fabric-loom-remap", use_mappings=True,
                          fabric_api="0.116.17+1.21.1", mc_range="~1.21.1", fabric_loader="0.20.1"),
    "fabric-26.3": dict(loader="fabric", minecraft="26.3", java=25, gradle="9.8.2",
                        loom_plugin="net.fabricmc.fabric-loom", use_mappings=False,
                        fabric_api="0.165.2+26.3", mc_range="~26.3", fabric_loader="0.20.1"),
    "neoforge-1.21.1": dict(loader="neoforge", minecraft="1.21.1", java=21, gradle="8.14.5",
                            neoforge="21.1.265", mc_range="[1.21.1,1.21.2)"),
    "neoforge-26.3": dict(loader="neoforge", minecraft="26.3", java=25, gradle="8.14.5",
                          neoforge="26.3.0.100", mc_range="[26.3,26.4)"),
}

MODS = {
    "pyhello-client": dict(
        package="pyhello_client",
        mod_id="pyhello_client",
        display="PyHello Client (Python)",
        description="Client-only Python smoke test for Python-for-Minecraft.",
        environment="client",
        phases={"client": "pyhello_client.entry:PyHelloClient"},
        python_files={
            "__init__.py": '''"""Client-only smoke test mod written in Python."""

MARKER = "[pyhello-client]"
''',
            "entry.py": '''"""Entry point and handlers of the client-only smoke test.

Every line this mod writes starts with ``[pyhello-client]`` so the smoke test in
``docs/testing.md`` can be checked with a single grep of the log.
"""
import pfm

from . import MARKER

TICKS_LOGGED = 0


class PyHelloClient:
    """Client entry point. Python-for-Minecraft constructs it and calls the hook."""

    def on_client_initialize(self):
        pfm.log.info("%s client entry point ran on the %s side" % (MARKER, pfm.side()))
        pfm.log.info("%s java interop: %s" % (MARKER, _java_probe()))


def _java_probe():
    """Proves Java interop: resolve a Java class through the bridge."""
    try:
        cls = pfm.java.import_class("net.minecraft.client.Minecraft")
        return "resolved %s" % cls
    except Exception as exc:  # noqa: BLE001 - reported, never fatal
        return "unavailable (%s)" % exc


@pfm.event("client_start")
def on_client_start(event):
    pfm.log.info("%s client_start, client handle present: %s"
                 % (MARKER, pfm.mc.client is not None))


@pfm.event("client_tick")
def on_client_tick(event):
    global TICKS_LOGGED
    TICKS_LOGGED += 1
    if TICKS_LOGGED in (1, 100):
        pfm.log.info("%s client_tick #%d" % (MARKER, TICKS_LOGGED))


@pfm.command("pyhello", usage="/pyhello")
def pyhello(ctx):
    ctx.reply("%s hello from client-side Python" % MARKER)
''',
        },
    ),
    "pyhello-common": dict(
        package="pyhello_common",
        mod_id="pyhello_common",
        display="PyHello Common (Python)",
        description="Common/server Python smoke test for Python-for-Minecraft.",
        environment="*",
        phases={"main": "pyhello_common.entry:PyHelloCommon",
                "server": "pyhello_common.entry:PyHelloCommon"},
        vendor=True,
        python_files={
            "__init__.py": '''"""Common/server smoke test mod written in Python."""

MARKER = "[pyhello-common]"
''',
            "entry.py": '''"""Entry point and handlers of the common/server smoke test.

The same module runs on the client and on a dedicated server; which hooks execute depends
on the side Python-for-Minecraft started the runtime on. It also imports ``six``, which is
vendored into this mod jar by ``tools/vendor_deps.py``.
"""
import pfm
import six

from . import MARKER

JOINS = 0


class PyHelloCommon:
    """Common entry point; both lifecycle hooks are side-specific."""

    def on_initialize(self):
        pfm.log.info("%s common entry point ran on the %s side" % (MARKER, pfm.side()))
        pfm.log.info("%s vendored dependency six %s is importable"
                     % (MARKER, six.__version__))

    def on_server_initialize(self):
        pfm.log.info("%s dedicated-server entry point ran" % MARKER)


@pfm.event("server_start")
def on_server_start(event):
    pfm.log.info("%s server_start, server handle present: %s"
                 % (MARKER, pfm.mc.server is not None))


@pfm.event("server_tick")
def on_server_tick(event):
    # Deliberately cheap: ticking handlers must not do work every tick.
    return None


@pfm.event("server_stop")
def on_server_stop(event):
    pfm.log.info("%s server_stop" % MARKER)


@pfm.event("player_join")
def on_player_join(event):
    global JOINS
    JOINS += 1
    pfm.log.info("%s player_join #%d: %s" % (MARKER, JOINS, event.data))


@pfm.command("pyhello", usage="/pyhello", permission=0)
def pyhello(ctx):
    ctx.reply("%s hello from Python on the %s side (six %s)"
              % (MARKER, pfm.side(), six.__version__))
''',
        },
    ),
}


def format_braces(text: str) -> str:
    """Re-indents a generated Kotlin DSL file by brace depth.

    Templates are indented Python strings with substituted blocks, so the raw output is not
    consistently indented. Kotlin does not care, but the files are committed and read by
    people, so they are normalised here.
    """
    depth = 0
    out = []
    for raw in text.split("\n"):
        line = raw.strip()
        if not line:
            out.append("")
            continue
        net = line.count("{") - line.count("}")
        indent = depth - 1 if line.startswith("}") else depth
        out.append("    " * max(0, indent) + line)
        depth = max(0, depth + net)
    return "\n".join(out).strip("\n") + "\n"


def write(path: str, content: str) -> None:
    full = os.path.join(REPO, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    text = textwrap.dedent(content).strip("\n") + "\n"
    if path.endswith(".kts"):
        text = format_braces(text)
    with open(full, "w", encoding="utf-8") as handle:
        handle.write(text)
    print("wrote", path)


def python_sources(name: str, mod: dict) -> None:
    for filename, content in mod["python_files"].items():
        write("examples/%s/python/%s/%s" % (name, mod["package"], filename), content)


def fabric_build(name: str, platform: str, mod: dict) -> None:
    cfg = PLATFORMS[platform]
    root = "examples/%s/%s" % (name, platform)
    write(root + "/settings.gradle.kts", """
        pluginManagement {
            repositories {
                maven {
                    name = "Fabric"
                    url = uri("https://maven.fabricmc.net/")
                }
                mavenCentral()
                gradlePluginPortal()
            }
        }

        dependencyResolutionManagement {
            versionCatalogs {
                create("libs") { from(files("../../../gradle/libs.versions.toml")) }
            }
        }

        rootProject.name = "%(mod_id)s-%(platform)s"
        """ % {"mod_id": mod["mod_id"], "platform": platform})

    write(root + "/gradle.properties", """
        org.gradle.jvmargs=-Xmx2G
        org.gradle.parallel=true
        minecraft_version=%(minecraft)s
        loader_version=%(fabric_loader)s
        fabric_api_version=%(fabric_api)s
        java_version=%(java)s
        version=1.0.0
        group=io.github.goshadows.examples
        """ % cfg)

    write(root + "/gradle/wrapper/gradle-wrapper.properties", """
        distributionBase=GRADLE_USER_HOME
        distributionPath=wrapper/dists
        distributionUrl=https\\://services.gradle.org/distributions/gradle-%(gradle)s-bin.zip
        networkTimeout=10000
        validateDistributionUrl=true
        zipStoreBase=GRADLE_USER_HOME
        zipStorePath=wrapper/dists
        """ % cfg)

    mappings = "    mappings(loom.officialMojangMappings())\n" if cfg["use_mappings"] else ""
    dep_config = "modImplementation" if cfg["use_mappings"] else "implementation"
    write(root + "/build.gradle.kts", """
        // Example Python mod: a normal Fabric mod jar whose entry point is Python.
        plugins {
            id("%(loom_plugin)s") version "%(loom)s"
        }

        val minecraft_version: String by project
        val loader_version: String by project
        val fabric_api_version: String by project
        val java_version: String by project

        base {
            archivesName.set("%(mod_id)s-fabric-%(minecraft)s")
        }

        repositories {
            mavenCentral()
        }

        dependencies {
            minecraft("com.mojang:minecraft:${minecraft_version}")
        %(mappings)s    %(dep_config)s("net.fabricmc:fabric-loader:${loader_version}")
            %(dep_config)s("net.fabricmc.fabric-api:fabric-api:${fabric_api_version}")
            // Compile-only: the language adapter and the core classes come from the
            // installed Python-for-Minecraft jars at runtime.
            compileOnly(files(
                "../../../platforms/fabric-%(minecraft)s/pyfm-core/build/libs/" +
                    "pythonforminecraft-core-fabric-%(minecraft)s-1.0.0-all.jar"
            ))
        }

        // This mod has no Java sources at all.
        sourceSets {
            named("main") {
                java.setSrcDirs(emptyList<String>())
            }
        }

        tasks.processResources {
            from("../python") {
                include("%(package)s/**")
                into("python")
            }
            from("../python") {
                include("vendor/**")
                into("python")
            }
            val version = project.version.toString()
            inputs.property("version", version)
            filesMatching("fabric.mod.json") {
                expand("version" to version)
            }
        }

        tasks.withType<JavaCompile>().configureEach {
            options.release.set(java_version.toInt())
        }

        java {
            toolchain {
                languageVersion.set(JavaLanguageVersion.of(java_version.toInt()))
            }
        }
        """ % dict(cfg, loom_plugin=cfg["loom_plugin"], loom="1.19", mappings=mappings,
                   dep_config=dep_config, mod_id=mod["mod_id"], package=mod["package"]))

    entrypoints = {}
    for key, value in mod["phases"].items():
        entrypoints[key] = [{"adapter": "python", "value": value}]
    depends = {
        "pythonforminecraft_core": ">=" + PYFM_VERSION,
        ("pythonforminecraft" if mod["environment"] == "client"
         else "pythonforminecraft_server"): ">=" + PYFM_VERSION,
        "fabricloader": ">=" + cfg["fabric_loader"],
        "minecraft": cfg["mc_range"],
        "java": ">=%s" % cfg["java"],
    }
    custom = {
        "python_root": "python",
        "modules": [mod["package"]],
    }
    if mod.get("vendor"):
        custom["vendor"] = ["python/vendor"]
    metadata = {
        "schemaVersion": 1,
        "id": mod["mod_id"],
        "version": "${version}",
        "name": mod["display"],
        "description": mod["description"],
        "authors": ["GoShadowS"],
        "contact": {"sources": "https://github.com/GoShadowS/Python-for-Minecraft"},
        "license": "Apache-2.0",
        "environment": mod["environment"],
        "entrypoints": entrypoints,
        "custom": {"pythonforminecraft": custom},
        "depends": depends,
    }
    write_json(root + "/src/main/resources/fabric.mod.json", metadata)


def write_json(path: str, data) -> None:
    """Writes metadata through json.dumps so the result is always valid and indented."""
    full = os.path.join(REPO, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=4)
        handle.write("\n")
    print("wrote", path)


def neoforge_build(name: str, platform: str, mod: dict) -> None:
    cfg = PLATFORMS[platform]
    root = "examples/%s/%s" % (name, platform)
    write(root + "/settings.gradle.kts", """
        pluginManagement {
            repositories {
                maven {
                    name = "NeoForged"
                    url = uri("https://maven.neoforged.net/releases")
                }
                mavenCentral()
                gradlePluginPortal()
            }
        }

        dependencyResolutionManagement {
            versionCatalogs {
                create("libs") { from(files("../../../gradle/libs.versions.toml")) }
            }
        }

        rootProject.name = "%(mod_id)s-%(platform)s"
        """ % {"mod_id": mod["mod_id"], "platform": platform})

    write(root + "/gradle.properties", """
        org.gradle.jvmargs=-Xmx2G
        org.gradle.parallel=true
        minecraft_version=%(minecraft)s
        neoforge_version=%(neoforge)s
        java_version=%(java)s
        version=1.0.0
        group=io.github.goshadows.examples
        """ % cfg)

    write(root + "/gradle/wrapper/gradle-wrapper.properties", """
        distributionBase=GRADLE_USER_HOME
        distributionPath=wrapper/dists
        distributionUrl=https\\://services.gradle.org/distributions/gradle-%(gradle)s-bin.zip
        networkTimeout=10000
        validateDistributionUrl=true
        zipStoreBase=GRADLE_USER_HOME
        zipStorePath=wrapper/dists
        """ % cfg)

    write(root + "/build.gradle.kts", """
        // Example Python mod: a normal NeoForge mod jar whose modLoader is
        // "pythonforminecraft", so it contains no Java code at all.
        plugins {
            id("net.neoforged.moddevgradle") version "2.0.90"
        }

        val neoforge_version: String by project
        val java_version: String by project

        base {
            archivesName.set("%(mod_id)s-neoforge-%(minecraft)s")
        }

        neoForge {
            version.set(neoforge_version)
        }

        // This mod has no Java sources at all.
        sourceSets {
            named("main") {
                java.setSrcDirs(emptyList<String>())
            }
        }

        tasks.processResources {
            from("../python") {
                include("%(package)s/**")
                into("python")
            }
            from("../python") {
                include("vendor/**")
                into("python")
            }
            val version = project.version.toString()
            inputs.property("version", version)
            filesMatching("META-INF/neoforge.mods.toml") {
                expand("version" to version)
            }
        }

        tasks.withType<JavaCompile>().configureEach {
            options.release.set(java_version.toInt())
        }

        java {
            toolchain {
                languageVersion.set(JavaLanguageVersion.of(java_version.toInt()))
            }
        }
        """ % dict(cfg, mod_id=mod["mod_id"], package=mod["package"]))

    pyfm_keys = {"main": "pyfm_main", "client": "pyfm_client", "server": "pyfm_server"}
    core_dep = ("pythonforminecraft" if mod["environment"] == "client"
                else "pythonforminecraft_server")
    lines = [
        'modLoader = "pythonforminecraft"',
        'loaderVersion = "[1,)"',
        'license = "Apache-2.0"',
        'issueTrackerURL = "https://github.com/GoShadowS/Python-for-Minecraft/issues"',
        "",
        "[[mods]]",
        'modId = "%s"' % mod["mod_id"],
        'version = "${version}"',
        'displayName = "%s"' % mod["display"],
        'authors = "GoShadowS"',
        'description = "%s"' % mod["description"],
        "",
    ]
    for dep_mod, version_range, side in (
            ("neoforge", "[21.1,)" if cfg["minecraft"] == "1.21.1" else "[26.3,)", "BOTH"),
            ("minecraft", cfg["mc_range"], "BOTH"),
            (core_dep, "[%s,)" % PYFM_VERSION, "BOTH")):
        lines += [
            "[[dependencies.%s]]" % mod["mod_id"],
            'modId = "%s"' % dep_mod,
            'type = "required"',
            'versionRange = "%s"' % version_range,
            'ordering = "%s"' % ("AFTER" if dep_mod == core_dep else "NONE"),
            'side = "%s"' % side,
            "",
        ]
    lines += ["[modproperties.%s]" % mod["mod_id"], 'python_root = "python"',
              'modules = ["%s"]' % mod["package"]]
    if mod.get("vendor"):
        lines.append('vendor = ["python/vendor"]')
    for key, value in mod["phases"].items():
        lines.append('%s = "%s"' % (pyfm_keys[key], value))
    write_raw(root + "/src/main/resources/META-INF/neoforge.mods.toml",
              "\n".join(lines) + "\n")


def write_raw(path: str, text: str) -> None:
    full = os.path.join(REPO, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8") as handle:
        handle.write(text)
    print("wrote", path)


def main() -> int:
    for name, mod in MODS.items():
        python_sources(name, mod)
        for platform, cfg in PLATFORMS.items():
            if cfg["loader"] == "fabric":
                fabric_build(name, platform, mod)
            else:
                neoforge_build(name, platform, mod)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
