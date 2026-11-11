#!/usr/bin/env python3
"""Generates the Gradle builds of Python-for-Minecraft for the four supported
loader/Minecraft combinations.

The generated files are committed; this script exists so the four builds cannot drift
apart.  Re-generate with::

    python3 tools/gen_builds.py

Every version number here is the one recorded in ``docs/sources.md``.  Values that could
not be resolved from a primary source inside the sandbox are marked ``TODO(verify)`` and
are listed as blockers in ``docs/testing.md``.
"""

from __future__ import annotations

import os
import textwrap

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

PYFM_VERSION = "1.0.0"
# Maven publishes GraalPy under a four-part version: the GraalVM release
# "graal-25.5.5" is artifact 25.5.5.0.3 (verified against
# repo1.maven.org/maven2/org/graalvm/polyglot/*/maven-metadata.xml).
GRAALPY = "25.5.5.0.3"
SLF4J = "2.0.17"
JUNIT = "5.11.4"
SHADOW = "9.2.2"
FABRIC_LOADER = "0.20.1"
# FabricMC/fabric-example-mod pins loom_version=1.19-SNAPSHOT on both the
# 1.21.1 and the 26.3 branch; there is no released "1.19" artifact.
LOOM = "1.19-SNAPSHOT"
# fabric-26.3 overrides this: Loom 1.19.4 fails to set up the unobfuscated 26.3 jars
# (ProviderNotFoundException: Provider "jar" not found), even for a single subproject.
FABRIC_GRADLE = "9.9.0"
# Gradle 8.14.5 fails on JDK 25: its bundled Kotlin compiler raises
# "IllegalArgumentException: 25.0.5". KotlinForForge 6.x pairs moddev 2.0.71 with
# gradle-9.6.1, so that combination is used here.
NEOFORGE_GRADLE = "9.6.1"
# ModDevGradle's plugin id is "net.neoforged.moddev" (NOT "moddevgradle") and the
# version is taken from thedarkcolour/KotlinForForge@6.x gradle/libs.versions.toml,
# which pins moddev = "2.0.71".
MODDEV_PLUGIN_ID = "net.neoforged.moddev"
MODDEVGRADLE = "2.0.148"

PLATFORMS = {
    "fabric-1.21.1": dict(
        loader="fabric", minecraft="1.21.1", java=21, gradle=FABRIC_GRADLE,
        loom_plugin="net.fabricmc.fabric-loom-remap", use_mappings=True,
        fabric_api="0.116.17+1.21.1", mc_range="~1.21.1",
    ),
    "fabric-26.3": dict(
        loader="fabric", minecraft="26.3", java=25, gradle=FABRIC_GRADLE,
        loom_plugin="net.fabricmc.fabric-loom", use_mappings=False,
        loom="1.20.0-alpha.27",
        fabric_api="0.165.2+26.3", mc_range="~26.3",
    ),
    "neoforge-1.21.1": dict(
        loader="neoforge", minecraft="1.21.1", java=21, gradle=NEOFORGE_GRADLE,
        neoforge="21.1.265", mc_range="[1.21.1,1.21.2)",
    ),
    "neoforge-26.3": dict(
        loader="neoforge", minecraft="26.3", java=25, gradle=NEOFORGE_GRADLE,
        neoforge="26.3.0.102", mc_range="[26.3,26.4)",
    ),
}

VERIFY_TASK = """
// Fails the build when the shaded jar lost something the Python runtime needs:
// Truffle discovers the Python language through a service file, and the pfm package
// has to be inside the jar so PyFmRuntimeResources can unpack it.
tasks.register("verifyPythonRuntime") {
    val output = tasks.named("shadowJar").flatMap {
        (it as com.github.jengelman.gradle.plugins.shadow.tasks.ShadowJar).archiveFile
    }
    inputs.files(output)
    doLast {
        val file = output.get().asFile
        val required = listOf(
            "META-INF/services/com.oracle.truffle.api.TruffleLanguage\$Provider",
            "pythonforminecraft/pfm/__init__.py",
        )
        JarFile(file).use { jar ->
            val missing = required.filter { jar.getJarEntry(it) == null }
            if (missing.isNotEmpty()) {
                throw GradleException("${file.name} is missing required entries: $missing")
            }
        }
        logger.lifecycle("verifyPythonRuntime: {} contains the Truffle service " +
                "registration and the pfm package", file.name)
    }
}

tasks.named("build") { dependsOn("verifyPythonRuntime") }
"""


ARTIFACTS = {
    "pyfm-core": dict(
        artifact="pythonforminecraft-core",
        fabric_id="pythonforminecraft_core",
        fabric_env="*",
        fabric_entrypoints=None,
        neoforge_mod=False,
    ),
    "pyfm-client": dict(
        artifact="pythonforminecraft-client",
        fabric_id="pythonforminecraft",
        fabric_env="client",
        fabric_entrypoints={"client": "io.github.goshadows.pythonforminecraft.fabric.PyFmClient"},
        neoforge_mod=True,
    ),
    "pyfm-server": dict(
        artifact="pythonforminecraft-server",
        fabric_id="pythonforminecraft_server",
        fabric_env="*",
        fabric_entrypoints={"main": "io.github.goshadows.pythonforminecraft.fabric.PyFmServer"},
        neoforge_mod=True,
    ),
}

DESCRIPTION = ("Python-for-Minecraft: run ordinary Minecraft mods written in Python. "
               "Language provider, comparable to Fabric Language Kotlin and Kotlin for "
               "Forge.")


def _reindent(content: str) -> str:
    """Normalises the indentation of a generated file.

    Templates are written inside indented Python strings, and some substituted blocks are
    deliberately flushed left; this re-indents the whole file by the indentation of its
    first non-empty line.
    """
    content = textwrap.dedent(content).strip("\n")
    lines = content.split("\n")
    first = next((line for line in lines if line.strip()), "")
    base = len(first) - len(first.lstrip(" "))
    if base == 0:
        return content + "\n"
    out = []
    for line in lines:
        if line.startswith(" " * base):
            out.append(line[base:])
        elif line.strip():
            out.append(" " * base + line)
        else:
            out.append("")
    return "\n".join(out) + "\n"


def format_braces(text: str) -> str:
    """Re-indents a generated Kotlin DSL or JSON file by brace depth.

    The templates mix Python-string indentation with substituted blocks, so the raw output
    is not consistently indented. Kotlin and JSON do not care, but the files are committed
    and read by people, so they are normalised here.
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
    text = _reindent(content)
    if path.endswith((".kts", ".json")):
        text = format_braces(text)
    with open(full, "w", encoding="utf-8") as handle:
        handle.write(text)
    print("wrote", path)


# --------------------------------------------------------------------------- version catalog
def catalog() -> None:
    write("gradle/libs.versions.toml", f"""
        # Shared version catalog. Every build in this repository reads it through
        # dependencyResolutionManagement, so the four platform builds cannot drift apart.
        # Sources for each version: docs/sources.md

        [versions]
        pyfm = "{PYFM_VERSION}"
        graalpy = "{GRAALPY}"
        slf4j = "{SLF4J}"
        junit = "{JUNIT}"
        shadow = "{SHADOW}"
        fabric-loader = "{FABRIC_LOADER}"
        loom = "{LOOM}"
        moddevgradle = "{MODDEVGRADLE}"

        [libraries]
        polyglot = {{ module = "org.graalvm.polyglot:polyglot", version.ref = "graalpy" }}
        python-community = {{ module = "org.graalvm.polyglot:python-community", version.ref = "graalpy" }}
        slf4j-api = {{ module = "org.slf4j:slf4j-api", version.ref = "slf4j" }}
        junit-jupiter = {{ module = "org.junit.jupiter:junit-jupiter", version.ref = "junit" }}
        fabric-loader = {{ module = "net.fabricmc:fabric-loader", version.ref = "fabric-loader" }}

        [bundles]
        graalpy = ["polyglot", "python-community"]

        [plugins]
        shadow = {{ id = "com.gradleup.shadow", version.ref = "shadow" }}
        """)


# -------------------------------------------------------------------------------- core build
def core_build() -> None:
    write("core/settings.gradle.kts", """
        // Standalone build of the loader-agnostic core, so its unit tests can run without a
        // Minecraft toolchain. The platform builds compile the same sources directly.
        pluginManagement {
            repositories {
                mavenCentral()
                gradlePluginPortal()
            }
        }

        dependencyResolutionManagement {
            versionCatalogs {
                create("libs") { from(files("../gradle/libs.versions.toml")) }
            }
        }

        rootProject.name = "pythonforminecraft-core"
        """)
    write("core/build.gradle.kts", f"""
        plugins {{
            `java-library`
        }}

        group = "io.github.goshadows"
        version = "{PYFM_VERSION}"

        java {{
            withSourcesJar()
        }}

        // No toolchain block: it would demand a specific installed JDK. Java 21 is
        // the bytecode floor for every supported combination, so release is enough.
        tasks.withType<JavaCompile>().configureEach {{
            options.release.set(21)
        }}

        repositories {{
            mavenCentral()
        }}

        dependencies {{
            // GraalPy is the Python runtime; see docs/architecture.md.
            api(libs.bundles.graalpy)
            compileOnly(libs.slf4j.api)

            testImplementation(libs.junit.jupiter)
            testImplementation(libs.slf4j.api)
            testRuntimeOnly("org.slf4j:slf4j-simple:${SLF4J}")
        }}

        tasks.test {{
            useJUnitPlatform()
            testLogging {{
                events("passed", "failed", "skipped")
            }}
        }}
        """)
    write("core/gradle.properties", f"""
        org.gradle.jvmargs=-Xmx2G
        org.gradle.parallel=true
        version={PYFM_VERSION}
        group=io.github.goshadows
        """)
    write("core/gradle/wrapper/gradle-wrapper.properties", f"""
        distributionBase=GRADLE_USER_HOME
        distributionPath=wrapper/dists
        distributionUrl=https\\://services.gradle.org/distributions/gradle-{NEOFORGE_GRADLE}-bin.zip
        networkTimeout=10000
        validateDistributionUrl=true
        zipStoreBase=GRADLE_USER_HOME
        zipStorePath=wrapper/dists
        """)


# ----------------------------------------------------------------------------- fabric builds
def fabric_settings(name: str, cfg: dict) -> None:
    write(f"platforms/{name}/settings.gradle.kts", f"""
        pluginManagement {{
            repositories {{
                maven {{
                    name = "Fabric"
                    url = uri("https://maven.fabricmc.net/")
                }}
                mavenCentral()
                gradlePluginPortal()
            }}
        }}

        dependencyResolutionManagement {{
            versionCatalogs {{
                create("libs") {{ from(files("../../gradle/libs.versions.toml")) }}
            }}
        }}

        rootProject.name = "pythonforminecraft-{name}"

        include("pyfm-core", "pyfm-client", "pyfm-server")
        """)


def fabric_properties(name: str, cfg: dict) -> None:
    write(f"platforms/{name}/gradle.properties", f"""
        org.gradle.jvmargs=-Xmx3G
        # The three subprojects share one Loom/ModDevGradle cache for the same Minecraft
        # version. Configuring them in parallel let one of them disown the cache lock and
        # rebuild it underneath the others -- run 42840517087, fabric-26.3: "Previous
        # process has disowned the lock due to abrupt termination", then "Failed to setup
        # Minecraft, ProviderNotFoundException: Provider jar not found".
        org.gradle.parallel=false

        # Keep loom_version in sync with the plugins block of build.gradle.kts.
        loom_version={cfg.get("loom", LOOM)}
        minecraft_version={cfg['minecraft']}
        loader_version={FABRIC_LOADER}
        fabric_api_version={cfg['fabric_api']}
        java_version={cfg['java']}
        pyfm_version={PYFM_VERSION}
        version={PYFM_VERSION}
        group=io.github.goshadows
        """)


def fabric_root(name: str, cfg: dict) -> None:
    write(f"platforms/{name}/build.gradle.kts", f"""
        // Minecraft {cfg['minecraft']} on Fabric. Java {cfg['java']}.
        // {"Mojang mappings + remapping." if cfg['use_mappings'] else "The game is unobfuscated, so no mappings line and no remapping."}
        plugins {{
            id("{cfg['loom_plugin']}") version "{cfg.get('loom', LOOM)}" apply false
            alias(libs.plugins.shadow) apply false
        }}

        subprojects {{
            group = rootProject.group.toString()
            version = rootProject.version.toString()
        }}
        """)


def fabric_wrapper(name: str, cfg: dict) -> None:
    write(f"platforms/{name}/gradle/wrapper/gradle-wrapper.properties", f"""
        distributionBase=GRADLE_USER_HOME
        distributionPath=wrapper/dists
        distributionUrl=https\\://services.gradle.org/distributions/gradle-{cfg['gradle']}-bin.zip
        networkTimeout=10000
        validateDistributionUrl=true
        zipStoreBase=GRADLE_USER_HOME
        zipStorePath=wrapper/dists
        """)


def fabric_mod_json(name: str, cfg: dict, sub: str, meta: dict) -> None:
    entrypoints = ""
    if meta["fabric_entrypoints"]:
        entries = ",\n".join(
            '            "%s": [\n                "%s"\n            ]' % (key, value)
            for key, value in meta["fabric_entrypoints"].items())
        entrypoints = ',\n    "entrypoints": {\n%s\n    }' % entries
    language_adapters = ""
    if sub == "pyfm-core":
        language_adapters = (',\n    "languageAdapters": {\n'
                             '        "python": "io.github.goshadows.pythonforminecraft'
                             '.fabric.PythonLanguageAdapter"\n    }')
    depends = {
        "fabricloader": f">={FABRIC_LOADER}",
        "minecraft": cfg["mc_range"],
        "java": f">={cfg['java']}",
    }
    if sub != "pyfm-core":
        depends["pythonforminecraft_core"] = f">={PYFM_VERSION}"
        depends["fabric-api"] = "*"
    depends_json = ",\n".join('        "%s": "%s"' % item for item in depends.items())
    write(f"platforms/{name}/{sub}/src/main/resources/fabric.mod.json", """
        {
            "schemaVersion": 1,
            "id": "%(id)s",
            "version": "${version}",
            "name": "%(name)s",
            "description": "%(description)s",
            "authors": [
                "GoShadowS"
            ],
            "contact": {
                "sources": "https://github.com/GoShadowS/Python-for-Minecraft"
            },
            "license": "Apache-2.0",
            "environment": "%(env)s"%(language_adapters)s%(entrypoints)s,
            "depends": {
        %(depends)s
            },
            "custom": {
                "pythonforminecraft:component": "%(sub)s"
            }
        }
        """ % {
            "id": meta["fabric_id"],
            "name": {
                "pyfm-core": "Python for Minecraft (core)",
                "pyfm-client": "Python for Minecraft (client)",
                "pyfm-server": "Python for Minecraft (server-capable)",
            }[sub],
            "description": DESCRIPTION,
            "env": meta["fabric_env"],
            "language_adapters": language_adapters,
            "entrypoints": entrypoints,
            "depends": depends_json,
            "sub": sub,
        })


def fabric_sub_build(name: str, cfg: dict, sub: str, meta: dict) -> None:
    remapped = cfg["use_mappings"]
    artifact = f"{meta['artifact']}-fabric-{cfg['minecraft']}"
    if sub == "pyfm-core":
        sources = ('listOf("../../../core/src/main/java", '
                   '"../../../loader-adapters/fabric/src/common/java")')
        extra_deps = """    // GraalPy is shaded into the core jar: Fabric only loads jars in
    // mods/ that are mods themselves, so the Python runtime cannot be a loose library jar.
    implementation(libs.bundles.graalpy)
    "shade"(libs.bundles.graalpy)"""
        python_resources = """
tasks.processResources {
    // The pfm package ships inside the core jar and is unpacked at start-up by
    // PyFmRuntimeResources.
    from("../../../python") {
        include("pfm/**")
        into("pythonforminecraft")
    }
}"""
    else:
        sources = ('listOf("../../../loader-adapters/fabric/src/%s/java")'
                   % ("client" if sub == "pyfm-client" else "server"))
        extra_deps = """    // Core classes are provided at runtime by the core jar; compiling
    // against it keeps them out of this artifact, so the jars never duplicate classes.
    compileOnly(project(":pyfm-core"))
    compileOnly(libs.bundles.graalpy)"""
        python_resources = ""

    mappings = '    mappings(loom.officialMojangMappings())\n' if remapped else ""
    loader_dep = ("modImplementation" if remapped else "implementation")
    api_dep = ("modImplementation" if remapped else "implementation")
    final_jar = """
tasks.remapJar {
    dependsOn(tasks.shadowJar)
    inputFile.set(tasks.shadowJar.get().archiveFile)
}""" if remapped else """
// Unobfuscated game: the shadow jar is the artifact, nothing is remapped.
tasks.jar { enabled = false }
tasks.assemble { dependsOn(tasks.shadowJar) }
tasks.build { dependsOn(tasks.shadowJar) }"""
    write(f"platforms/{name}/{sub}/build.gradle.kts", """
        plugins {
            id("%(loom)s")
            alias(libs.plugins.shadow)
        }

        val minecraft_version: String = project.property("minecraft_version") as String
        val loader_version: String = project.property("loader_version") as String
        val fabric_api_version: String = project.property("fabric_api_version") as String
        val java_version: String = project.property("java_version") as String

        base {
            archivesName.set("%(artifact)s")
        }

        // Dependencies that are shaded into the artifact instead of being resolved at
        // runtime. Fabric and NeoForge both only load jars that are mods/libraries, so the
        // Python runtime has to travel inside the core jar.
        // Shadow expands every file in this configuration as a ZIP. Created without
        // attributes, Gradle resolves it the legacy way, where the artifact of a
        // pom-packaging module is the POM file itself -- that is why shadowJar died on
        // "Cannot expand ZIP .../python-community-25.5.5.0.3.pom" on every platform.
        // With runtime attributes Gradle matches variants instead, so an aggregator POM
        // contributes its dependencies (real jars) and no artifact of its own.
        val shade: Configuration = configurations.create("shade") {
            isCanBeConsumed = false
            isCanBeResolved = true
            attributes {
                // Fully qualified on purpose: this must not depend on the Kotlin DSL
                // implicit imports being present.
                attribute(org.gradle.api.attributes.Usage.USAGE_ATTRIBUTE,
                        objects.named(org.gradle.api.attributes.Usage::class.java,
                                org.gradle.api.attributes.Usage.JAVA_RUNTIME))
                attribute(org.gradle.api.attributes.Category.CATEGORY_ATTRIBUTE,
                        objects.named(org.gradle.api.attributes.Category::class.java,
                                org.gradle.api.attributes.Category.LIBRARY))
                attribute(org.gradle.api.attributes.LibraryElements.LIBRARY_ELEMENTS_ATTRIBUTE,
                        objects.named(org.gradle.api.attributes.LibraryElements::class.java,
                                org.gradle.api.attributes.LibraryElements.JAR))
                attribute(org.gradle.api.attributes.Bundling.BUNDLING_ATTRIBUTE,
                        objects.named(org.gradle.api.attributes.Bundling::class.java,
                                org.gradle.api.attributes.Bundling.EXTERNAL))
            }
        }

        loom {
            // No split source sets: this build has one side per subproject by design.
        }

        dependencies {
            minecraft("com.mojang:minecraft:${minecraft_version}")
        %(mappings)s    %(loader_dep)s("net.fabricmc:fabric-loader:${loader_version}")
            %(api_dep)s("net.fabricmc.fabric-api:fabric-api:${fabric_api_version}")
            compileOnly(libs.slf4j.api)
        %(extra_deps)s
        }

        sourceSets {
            named("main") {
                java.setSrcDirs(%(sources)s)
            }
        }
        %(python_resources)s
        tasks.withType<JavaCompile>().configureEach {
            options.release.set(java_version.toInt())
            options.encoding = "UTF-8"
        }

        // No toolchain block on purpose: options.release above pins the bytecode
        // level, while the build JVM itself must satisfy the Gradle plugin
        // (Loom 1.19 needs JDK 25 even for Minecraft 1.21.1).

        tasks.processResources {
            val version = project.version.toString()
            inputs.property("version", version)
            filesMatching("fabric.mod.json") {
                expand("version" to version)
            }
        }

        // Shadow expands everything it is given as a ZIP, so it gets jars and nothing else.
        // Two GraalPy modules -- org.graalvm.python:python-community and
        // org.graalvm.python:python -- are POM aggregators: they pull in python-language,
        // python-resources, truffle-runtime, truffle-compiler, regex, icu4j and the rest as
        // real jars, but Gradle still lists their POM among the resolved artifacts, and
        // shadowJar died on "Cannot expand ZIP .../python-community-25.5.5.0.3.pom".
        // Filtering here keeps every real GraalPy jar in the mod jar and drops only the POMs.
        val shadeArtifacts = project.configurations.named("shade").get()
                .incoming.artifactView { it.lenient(false) }.artifacts

        tasks.shadowJar {
            configurations = listOf()
            from(provider {
                shadeArtifacts.artifacts
                        .filter { it.file.name.endsWith(".jar") }
                        .map { zipTree(it.file) }
            })
            archiveClassifier.set("all")
            mergeServiceFiles()
            exclude("META-INF/*.SF", "META-INF/*.DSA", "META-INF/*.RSA")
            exclude("module-info.class")
        }
        %(final_jar)s
        """ % {
            "loom": cfg["loom_plugin"],
            "verify": (VERIFY_TASK if sub == "pyfm-core" else ""),
            "artifact": artifact,
            "mappings": mappings,
            "loader_dep": loader_dep,
            "api_dep": api_dep,
            "extra_deps": extra_deps,
            "sources": sources,
            "python_resources": python_resources,
            "final_jar": final_jar,
            "verify": (VERIFY_TASK if sub == "pyfm-core" else ""),
        })


# ---------------------------------------------------------------------------- neoforge builds
def neoforge_settings(name: str, cfg: dict) -> None:
    write(f"platforms/{name}/settings.gradle.kts", f"""
        pluginManagement {{
            repositories {{
                maven {{
                    name = "NeoForged"
                    url = uri("https://maven.neoforged.net/releases")
                }}
                mavenCentral()
                gradlePluginPortal()
            }}
        }}

        dependencyResolutionManagement {{
            versionCatalogs {{
                create("libs") {{ from(files("../../gradle/libs.versions.toml")) }}
            }}
        }}

        rootProject.name = "pythonforminecraft-{name}"

        include("pyfm-core", "pyfm-client", "pyfm-server")
        """)


def neoforge_properties(name: str, cfg: dict) -> None:
    write(f"platforms/{name}/gradle.properties", f"""
        org.gradle.jvmargs=-Xmx3G
        # The three subprojects share one Loom/ModDevGradle cache for the same Minecraft
        # version. Configuring them in parallel let one of them disown the cache lock and
        # rebuild it underneath the others -- run 42840517087, fabric-26.3: "Previous
        # process has disowned the lock due to abrupt termination", then "Failed to setup
        # Minecraft, ProviderNotFoundException: Provider jar not found".
        org.gradle.parallel=false

        minecraft_version={cfg['minecraft']}
        neoforge_version={cfg['neoforge']}
        java_version={cfg['java']}
        pyfm_version={PYFM_VERSION}
        version={PYFM_VERSION}
        group=io.github.goshadows
        """)


def neoforge_root(name: str, cfg: dict) -> None:
    write(f"platforms/{name}/build.gradle.kts", f"""
        // Minecraft {cfg['minecraft']} on NeoForge. Java {cfg['java']}.
        plugins {{
            id("{MODDEV_PLUGIN_ID}") version "{MODDEVGRADLE}" apply false
            alias(libs.plugins.shadow) apply false
        }}

        subprojects {{
            group = rootProject.group.toString()
            version = rootProject.version.toString()
        }}
        """)


def neoforge_wrapper(name: str, cfg: dict) -> None:
    write(f"platforms/{name}/gradle/wrapper/gradle-wrapper.properties", f"""
        distributionBase=GRADLE_USER_HOME
        distributionPath=wrapper/dists
        distributionUrl=https\\://services.gradle.org/distributions/gradle-{cfg['gradle']}-bin.zip
        networkTimeout=10000
        validateDistributionUrl=true
        zipStoreBase=GRADLE_USER_HOME
        zipStorePath=wrapper/dists
        """)


def neoforge_mods_toml(name: str, cfg: dict, sub: str, meta: dict) -> None:
    if sub == "pyfm-core":
        # The core jar is a plugin-layer library, not a mod: no neoforge.mods.toml.
        write(f"platforms/{name}/{sub}/src/main/resources/META-INF/services/"
              "net.neoforged.neoforgespi.language.IModLanguageLoader", """
            io.github.goshadows.pythonforminecraft.neoforge.PythonNeoForgeLoader
            """)
        return
    mod_id = meta["fabric_id"]
    write(f"platforms/{name}/{sub}/src/main/resources/META-INF/neoforge.mods.toml", """
        modLoader = "javafml"
        loaderVersion = "[4,)"
        license = "Apache-2.0"
        issueTrackerURL = "https://github.com/GoShadowS/Python-for-Minecraft/issues"

        [[mods]]
        modId = "%(mod_id)s"
        version = "${version}"
        displayName = "%(name)s"
        authors = "GoShadowS"
        description = '''
        %(description)s
        '''

        [[dependencies.%(mod_id)s]]
        modId = "neoforge"
        type = "required"
        versionRange = "[21.1,)"
        ordering = "NONE"
        side = "BOTH"

        [[dependencies.%(mod_id)s]]
        modId = "minecraft"
        type = "required"
        versionRange = "%(mc_range)s"
        ordering = "NONE"
        side = "BOTH"

        [[dependencies.%(mod_id)s]]
        modId = "pythonforminecraft_core"
        type = "required"
        versionRange = "[%(pyfm)s,)"
        ordering = "AFTER"
        side = "BOTH"
        """ % {
            "mod_id": mod_id,
            "name": {
                "pyfm-client": "Python for Minecraft (client)",
                "pyfm-server": "Python for Minecraft (server-capable)",
            }[sub],
            "description": DESCRIPTION,
            "mc_range": cfg["mc_range"],
            "pyfm": PYFM_VERSION,
        })


def neoforge_sub_build(name: str, cfg: dict, sub: str, meta: dict) -> None:
    artifact = f"{meta['artifact']}-neoforge-{cfg['minecraft']}"
    # FMLEnvironment exposes the side as a field on FML 4.x (Minecraft 1.21.1) and as a
    # method on the FML line behind NeoForge 26.3, so side detection lives in one small
    # class per target and every NeoForge subproject compiles it next to its own sources.
    compat = "../../../loader-adapters/neoforge/src/compat-%s/java" % cfg["minecraft"]
    if sub == "pyfm-core":
        sources = ('listOf("../../../core/src/main/java", '
                   '"../../../loader-adapters/neoforge/src/lang/java", "%s")'
                   % compat)
        mdg = """
neoForge {
    version = neoforge_version
}"""
        manifest = """
tasks.jar {
    manifest {
        // FML loads the Python mod loader from the plugin layer, which requires a LIBRARY
        // jar without a neoforge.mods.toml -- the same shape Kotlin for Forge uses.
        attributes(
            "FMLModType" to "LIBRARY",
            "Implementation-Version" to project.version.toString(),
        )
    }
}"""
        extra = """    implementation(libs.bundles.graalpy)
    "shade"(libs.bundles.graalpy)"""
        python_resources = """
tasks.processResources {
    from("../../../python") {
        include("pfm/**")
        into("pythonforminecraft")
    }
}"""
    else:
        sources = ('listOf("../../../loader-adapters/neoforge/src/%s/java", '
                   '"%s")'
                   % ("client" if sub == "pyfm-client" else "server", compat))
        mdg = """
neoForge {
    version = neoforge_version
    runs {
        register("client") { client() }
        register("server") { server() }
    }
}"""
        manifest = ""
        extra = """    compileOnly(project(":pyfm-core"))
    compileOnly(libs.bundles.graalpy)"""
        python_resources = ""
    plugins = ('id("%s")\n    alias(libs.plugins.shadow)' % MODDEV_PLUGIN_ID
               if sub != "pyfm-core" else
               '`java-library`\n    id("%s")\n    alias(libs.plugins.shadow)'
               % MODDEV_PLUGIN_ID)
    write(f"platforms/{name}/{sub}/build.gradle.kts", """
        %(imports)splugins {
            %(plugins)s
        }

        val neoforge_version: String = project.property("neoforge_version") as String
        val java_version: String = project.property("java_version") as String

        base {
            archivesName.set("%(artifact)s")
        }

        // See the fabric builds: shaded dependencies travel inside the core jar.
        // Shadow expands every file in this configuration as a ZIP. Created without
        // attributes, Gradle resolves it the legacy way, where the artifact of a
        // pom-packaging module is the POM file itself -- that is why shadowJar died on
        // "Cannot expand ZIP .../python-community-25.5.5.0.3.pom" on every platform.
        // With runtime attributes Gradle matches variants instead, so an aggregator POM
        // contributes its dependencies (real jars) and no artifact of its own.
        val shade: Configuration = configurations.create("shade") {
            isCanBeConsumed = false
            isCanBeResolved = true
            attributes {
                // Fully qualified on purpose: this must not depend on the Kotlin DSL
                // implicit imports being present.
                attribute(org.gradle.api.attributes.Usage.USAGE_ATTRIBUTE,
                        objects.named(org.gradle.api.attributes.Usage::class.java,
                                org.gradle.api.attributes.Usage.JAVA_RUNTIME))
                attribute(org.gradle.api.attributes.Category.CATEGORY_ATTRIBUTE,
                        objects.named(org.gradle.api.attributes.Category::class.java,
                                org.gradle.api.attributes.Category.LIBRARY))
                attribute(org.gradle.api.attributes.LibraryElements.LIBRARY_ELEMENTS_ATTRIBUTE,
                        objects.named(org.gradle.api.attributes.LibraryElements::class.java,
                                org.gradle.api.attributes.LibraryElements.JAR))
                attribute(org.gradle.api.attributes.Bundling.BUNDLING_ATTRIBUTE,
                        objects.named(org.gradle.api.attributes.Bundling::class.java,
                                org.gradle.api.attributes.Bundling.EXTERNAL))
            }
        }

        repositories {
            maven {
                name = "NeoForged"
                url = uri("https://maven.neoforged.net/releases")
            }
            mavenCentral()
        }
        %(mdg)s
        dependencies {
            // No explicit slf4j-api here: net.neoforged:neoforge already puts
            // org.slf4j:slf4j-api:{strictly 2.0.9} on the compile classpath through
            // minecraft-dependencies, and a strict constraint cannot be overridden --
            // pinning 2.0.17 made resolution fail outright (run 42842100723).
        %(extra)s
        }

        sourceSets {
            named("main") {
                java.setSrcDirs(%(sources)s)
            }
        }
        %(python_resources)s
        tasks.withType<JavaCompile>().configureEach {
            options.release.set(java_version.toInt())
            options.encoding = "UTF-8"
        }

        // No toolchain block on purpose; see the fabric builds.
        %(manifest)s
        // Shadow expands everything it is given as a ZIP, so it gets jars and nothing else.
        // Two GraalPy modules -- org.graalvm.python:python-community and
        // org.graalvm.python:python -- are POM aggregators: they pull in python-language,
        // python-resources, truffle-runtime, truffle-compiler, regex, icu4j and the rest as
        // real jars, but Gradle still lists their POM among the resolved artifacts, and
        // shadowJar died on "Cannot expand ZIP .../python-community-25.5.5.0.3.pom".
        // Filtering here keeps every real GraalPy jar in the mod jar and drops only the POMs.
        val shadeArtifacts = project.configurations.named("shade").get()
                .incoming.artifactView { it.lenient(false) }.artifacts

        tasks.shadowJar {
            configurations = listOf()
            from(provider {
                shadeArtifacts.artifacts
                        .filter { it.file.name.endsWith(".jar") }
                        .map { zipTree(it.file) }
            })
            archiveClassifier.set("all")
            mergeServiceFiles()
            exclude("META-INF/*.SF", "META-INF/*.DSA", "META-INF/*.RSA")
            exclude("module-info.class")
        }

        tasks.jar {
            dependsOn(tasks.shadowJar)
        }
        %(verify)s
        """ % {
            "plugins": plugins,
            "imports": ("import java.util.jar.JarFile\n\n" if sub == "pyfm-core" else ""),
            "verify": (VERIFY_TASK if sub == "pyfm-core" else ""),
            "artifact": artifact,
            "mdg": mdg,
            "extra": extra,
            "sources": sources,
            "python_resources": python_resources,
            "manifest": manifest,
        })


# ------------------------------------------------------------------------------------- main
def main() -> int:
    catalog()
    core_build()
    for name, cfg in PLATFORMS.items():
        if cfg["loader"] == "fabric":
            fabric_settings(name, cfg)
            fabric_properties(name, cfg)
            fabric_root(name, cfg)
            fabric_wrapper(name, cfg)
            for sub, meta in ARTIFACTS.items():
                fabric_sub_build(name, cfg, sub, meta)
                fabric_mod_json(name, cfg, sub, meta)
        else:
            neoforge_settings(name, cfg)
            neoforge_properties(name, cfg)
            neoforge_root(name, cfg)
            neoforge_wrapper(name, cfg)
            for sub, meta in ARTIFACTS.items():
                neoforge_sub_build(name, cfg, sub, meta)
                neoforge_mods_toml(name, cfg, sub, meta)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
