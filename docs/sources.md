# Primary sources used

Everything below was read on **2026-11-10** from the upstream project itself (GitHub API /
repository content) or from the projects' own documentation. Where a fact could not be read
from a primary source in this sandbox it is marked `[UNVERIFIED-HERE]`.

## Minecraft versions

| Fact | Source |
|---|---|
| 26.3 "Wilderness Bound" released 2026-09-15, calendar versioning (26.1 = first 2026 drop), Java **25** required, protocol 777 | https://minecraft.wiki/w/Java_Edition_26.3_Snapshot_3 (infobox: "Minimum Java version: Java SE 25"), https://mcreference.com/minecraft-versions/26.3 |
| 1.21.x line runs on Java 21; 1.21.11 was the last `1.`-prefixed version | https://1up-servers.com/en/blog/minecraft-version-numbers-explained/ |
| 26.x ships **deobfuscated** (26.3 client jar: 10,737 real `net/minecraft/` classes, 0 obfuscated; 1.21.11: 33 real / 10,201 obfuscated) | https://github.com/lhns/mc-dependency-provider/pull/35 (upstream investigation, quoted counts) |

## Fabric

| Fact | Source |
|---|---|
| 1.21.1 template: `loader_version=0.20.1`, `loom_version=1.19-SNAPSHOT`, plugin `net.fabricmc.fabric-loom-remap`, `mappings loom.officialMojangMappings()`, `modImplementation`, Java 21, `fabric_api_version=0.116.17+1.21.1` | `FabricMC/fabric-example-mod@1.21.1`: `gradle.properties`, `build.gradle` |
| 26.3 template: same loader/loom, plugin **`net.fabricmc.fabric-loom`** (non-remapping), **no `mappings`**, `implementation`, Java 25, `fabric_api_version=0.165.2+26.3` | `FabricMC/fabric-example-mod@26.3`: `gradle.properties`, `build.gradle` |
| `LanguageAdapter` interface: `<T> T create(ModContainer mod, String value, Class<T> type) throws LanguageAdapterException`; adapters are declared in `fabric.mod.json` → `languageAdapters`; the declaring class needs a public no-arg constructor | `FabricMC/fabric-loader@0.20.1`: `src/main/java/net/fabricmc/loader/api/LanguageAdapter.java` |
| Entry point interfaces `ModInitializer#onInitialize` (`main`), `ClientModInitializer#onInitializeClient` (`client`), `DedicatedServerModInitializer#onInitializeServer` (`server`), all `@FunctionalInterface` | `FabricMC/fabric-loader@0.20.1`: `src/main/java/net/fabricmc/api/*.java` |
| FLK usage pattern: `{"adapter":"kotlin","value":"mymod.MyMod"}`, `schemaVersion` must be 1, `depends.fabric-language-kotlin`; FLK is a mod jar that bundles libraries and declares the adapter | https://github.com/FabricMC/fabric-language-kotlin (README), latest release `1.14.2+kotlin.2.4.21` (2026-10-09) |
| Loom 1.19 is a released version (2026-10-23) | GitHub API `repos/FabricMC/fabric-loom/releases` |
| Fabric Loader releases: 0.19.5 (2026-08-28), 0.20.0 (2026-10-15), 0.20.1 (2026-10-19) | GitHub API `repos/FabricMC/fabric-loader/releases` |

## NeoForge / FancyModLoader

| Fact | Source |
|---|---|
| `IModLanguageLoader`: `name()`, `version()`, `loadMod(IModInfo, ModFileScanData, ModuleLayer)`, `default validate(IModFile, Collection<ModContainer>, IIssueReporting)`; "Loaded as a ServiceLoader, from the plugin layer. Jars in the mods directory must have an `FMLModType` of `LIBRARY`"; "Version data is read from the manifest's implementation version" | `neoforged/FancyModLoader@1.21.1` and `@11.x`: `loader/src/main/java/net/neoforged/neoforgespi/language/IModLanguageLoader.java` (byte-identical on both branches) |
| `ModContainer`: `public ModContainer(IModInfo)`, `protected void constructMod()`, `public abstract IEventBus getEventBus()` | `neoforged/FancyModLoader@1.21.1` and `@11.x`: `loader/src/main/java/net/neoforged/fml/ModContainer.java` (identical) |
| `IModInfo#getModProperties()` exists; FML parses `[modproperties.<modId>]` into it | `neoforged/FancyModLoader@1.21.1`: `IModInfo.java`, `moddiscovery/ModInfo.java` line 107 |
| `neoforge.mods.toml` file-level keys parsed by FML: `modLoader`, `loaderVersion`, `license`, `showAsResourcePack`, `showAsDataPack`, `services`, `properties`, `issueTrackerURL`; per-mod keys: `modId`, `namespace`, `version`, `displayName`, `description`, `logoFile`, `logoBlur`, `updateJSONURL`, `modUrl`, `modproperties`. **No `clientOnly`/`serverOnly`, no `entryPoint`.** | `neoforged/FancyModLoader@1.21.1` / `@11.x`: `moddiscovery/ModFileInfo.java`, `moddiscovery/ModInfo.java` |
| KFF is the reference: `modLoader="kotlinforforge"`, `loaderVersion="[5,)"`; ships `kfflang` jar with `FMLModType: LIBRARY` + `META-INF/services/net.neoforged.neoforgespi.language.IModLanguageLoader`, `kfflib` with `FMLModType: GAMELIBRARY`, `kffmod` as the mod; `KotlinLanguageLoader` implements the SPI; `KotlinModContainer extends ModContainer` | `thedarkcolour/KotlinForForge@6.x`: `README.md`, `build.gradle.kts`, `src/kfflang/kotlin/.../KotlinLanguageLoader.kt`, `KotlinModContainer.kt`, `src/kffmod/templates/META-INF/neoforge.mods.toml` |
| KFF 6.x targets MC 1.21.9+ (`min_mc_version=1.21.9`, `unsupported_mc_version=26.4`), Java 25 toolchain, version 6.5.0 | `thedarkcolour/KotlinForForge@6.x`: `gradle.properties`, `build.gradle.kts` |
| NeoForge lines: `21.1.x` for MC 1.21.1 (Java 21), `26.3.0.x` for MC 26.3 (Java 25); NeoForge git tags `26.3.0`, `26.3.0-stable` | GitHub API `repos/neoforged/NeoForge/tags`; https://space-node.net/blog/neoforge-download-install-guide-2026 (latest 1.21.1 build 21.1.265, 26.3 build 26.3.0.100) |
| ModDevGradle is the current NeoForge Gradle plugin (`net.neoforged.moddevgradle`), `2.0` line; KFF imports `net.neoforged.moddevgradle.tasks.JarJar` | `thedarkcolour/KotlinForForge@6.x`: `build.gradle.kts`; GitHub API `repos/neoforged/ModDevGradle/tags` |

## GraalPy

| Fact | Source |
|---|---|
| Latest release `graal-25.5.5` "GraalPy3.13 25.5.5", 2026-11-03 | GitHub API `repos/oracle/graalpython/releases` |
| "GraalPy is a high-performance implementation of the Python language for the JVM … Python 3.13 compliant runtime … first-class support for embedding in Java" | https://github.com/oracle/graalpython |
| Embedding artifacts: `org.graalvm.polyglot:polyglot`, `org.graalvm.polyglot:python-community` (Community) / `:python` (Oracle GraalVM), `org.graalvm.python:python-embedding` (UPL-licensed helper, `GraalPyResources.contextBuilder()`) | https://graalpy.org/jvm-developers/docs/ ; https://central.sonatype.com/artifact/org.graalvm.python/python-embedding |
| Java access from Python: `import java; java.type("java.math.BigInteger")`, `from java.util import ArrayList`; foreign objects appear as `polyglot.ForeignObject` subclasses | `oracle/graalpython`: `docs/user/Interoperability.md` |
| License of the repository: `LICENSE.txt` = "Universal Permissive License (UPL) v. 1.0", "Copyright (c) 2018, 2026, Oracle and/or its affiliates"; a `THIRD_PARTY_LICENSE.txt` also exists | GitHub API `repos/oracle/graalpython/contents/LICENSE.txt` |
| `[UNVERIFIED-HERE]` license texts inside the published Maven artifacts, and their exact sizes | Maven Central is not reachable from this sandbox |

## Alternatives that were rejected

| Option | Source consulted | Reason |
|---|---|---|
| Chicory (`com.dylibso.chicory`, latest 1.7.5, 2026-03-24) running CPython compiled to WASM | GitHub API `repos/dylibso/chicory/releases` | pure JVM but Python cannot see Java objects without a hand-written host bridge |
| Jython | project state | Python 2.7 only, unmaintained |
| CPython over JNI (Jep-style) | — | per-OS native payload, breaks single-artifact distribution |

## Environment facts of this sandbox (limits on verification)

| Check | Result |
|---|---|
| `java` / `javac` | not installed (`command not found`) |
| `gradle` | not installed |
| `apt-get update` | fails: `/var/lib/apt/lists/partial … Permission denied` — no JDK can be installed |
| `repo1.maven.org`, `maven.fabricmc.net`, `piston-meta.mojang.com` | TLS connection refused (egress allow-list) |
| `api.github.com`, `pypi.org` | reachable (200) |
| Python available for running the Python layer | `Python 3.11.2` |
