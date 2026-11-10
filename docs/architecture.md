# Python-for-Minecraft — architecture and runtime choice

Status: **design record**. Every version number and API signature below was read from a
primary source on 2026-11-10; see [`sources.md`](sources.md) for the exact URLs. Items that
could **not** be verified inside this development environment are marked
`[UNVERIFIED-HERE]` and are repeated in [`testing.md`](testing.md).

---

## 1. Goal and scope

Python-for-Minecraft is a **language provider** for Minecraft mods: the JVM-side analogue of
[Fabric Language Kotlin](https://github.com/FabricMC/fabric-language-kotlin) (FLK) and
[Kotlin for Forge](https://github.com/thedarkcolour/KotlinForForge) (KFF), but for Python.

A *Python mod* is an ordinary Minecraft mod JAR — its own mod id, its own loader metadata,
its own resources — that depends on Python-for-Minecraft and whose entry points are Python
objects. Python-for-Minecraft is not a bot, not an RCON bridge, not a separate game and not
an in-game console: the Python code runs **inside the game JVM**, on the side (client /
dedicated server) where the mod declares it.

Out of scope (deliberately): reimplementing a Minecraft API surface of our own. Python code
reaches the game through Java interop; whatever the Java/Minecraft/loader API exposes is what
Python can reach.

---

## 2. Target matrix — verified facts

| Combination | Minecraft | Java | Loader | Loader metadata | Dev toolchain |
|---|---|---|---|---|---|
| Fabric + 1.21.1 | 1.21.1 | 21 | Fabric Loader `0.20.1` | `fabric.mod.json` (schema 1) | Loom `1.19`, plugin id `net.fabricmc.fabric-loom-remap`, `mappings loom.officialMojangMappings()`, `modImplementation`, Fabric API `0.116.17+1.21.1` |
| NeoForge + 1.21.1 | 1.21.1 | 21 | NeoForge `21.1.x` (latest line build `21.1.265`) | `META-INF/neoforge.mods.toml` | ModDevGradle `2.0.x` |
| Fabric + 26.3 | 26.3 | **25** | Fabric Loader `0.20.1` | `fabric.mod.json` (schema 1) | Loom `1.19`, plugin id **`net.fabricmc.fabric-loom`** (non-remapping), **no `mappings` line**, **`implementation` instead of `modImplementation`**, `jar` instead of `remapJar`, Fabric API `0.165.2+26.3` |
| NeoForge + 26.3 | 26.3 | **25** | NeoForge `26.3.0.x` (tags `26.3.0`, `26.3.0-stable`) | `META-INF/neoforge.mods.toml` | ModDevGradle `2.0.x` |

Facts that shaped the design:

1. **Minecraft 26.x ships deobfuscated.** The 26.3 client jar contains real
   `net/minecraft/...` names and no obfuscated ones, Mojang publishes no `client_mappings`
   for the line, and Fabric has no Yarn builds for 26.x. Consequence: for 26.x Fabric uses
   the *non-remapping* Loom plugin, plain `implementation` dependencies and `jar`; a 1.21.1
   Fabric build keeps using the remapping plugin and Mojang mappings. **One Gradle
   configuration therefore cannot serve both Fabric versions**, and the artifacts are not
   interchangeable.
2. **Java differs per line**: 21 for 1.21.1, 25 for 26.x. The four builds use per-build
   Gradle toolchains and are separate Gradle builds, not one.
3. **Fabric discovers entry points declaratively** (`fabric.mod.json` → `entrypoints`), and a
   *language adapter* (`net.fabricmc.loader.api.LanguageAdapter`,
   `<T> T create(ModContainer, String, Class<T>)`, registered through `languageAdapters`)
   decides how a `value` string becomes an object. This is exactly how FLK works
   (`{"adapter": "kotlin", "value": "mymod.MyMod"}`).
4. **NeoForge has no `fabric.mod.json` equivalent of adapters**; it has a *mod loader SPI*:
   `net.neoforged.neoforgespi.language.IModLanguageLoader`
   (`name()`, `version()`, `loadMod(IModInfo, ModFileScanData, ModuleLayer)`,
   `validate(IModFile, Collection<ModContainer>, IIssueReporting)`), discovered with
   `ServiceLoader` **from the plugin layer**, and selected per mod file by
   `modLoader="…"` + `loaderVersion="[…)"` in `neoforge.mods.toml`. A jar that provides it
   must carry the manifest attribute `FMLModType: LIBRARY`. KFF does exactly this
   (`modLoader="kotlinforforge"`). The SPI source is **identical** on the
   `1.21.1` and `11.x` (26.x) branches of `neoforged/FancyModLoader`, so one implementation
   serves both NeoForge lines.
5. `neoforge.mods.toml` has no `entryPoint` key. Custom per-mod data is read from
   `[modproperties.<modId>]`, which FML parses into `IModInfo#getModProperties()`.
   There is no `clientOnly`/`serverOnly` mod-file flag in FML's parser — side separation on
   NeoForge is done with separate jars plus `Dist` guards.

---

## 3. Python runtime: options considered

| Option | Python | In-JVM | Java interop | Cross-platform single artifact | Verdict |
|---|---|---|---|---|---|
| **GraalPy** (`org.graalvm.polyglot:python-community`, 25.5.5, 2026-11-03) | **3.13** | yes, pure JVM | first class: `import java; java.type("…")`, host objects passed as bindings | yes (jars, no native code required) | **chosen** |
| Chicory + CPython-WASM (`com.dylibso.chicory`, 1.7.5) | 3.11/3.13 CPython | yes, pure JVM | poor: Python sees WASI, not Java objects; every call needs a hand-written host bridge | yes | rejected: Java interop is the core requirement |
| Jython | 2.7 only | yes | good | yes | rejected: Python 2, unmaintained |
| CPython + JNI (Jep, py4j-embeddings) | 3.x | partially | good | **no** — per-OS native builds | rejected: breaks single-artifact distribution |
| Separate Python process / socket / RCON bridge | any | **no** | n/a | n/a | rejected by the brief: must be an in-JVM language provider |

Why GraalPy:

* modern Python 3.13 (release `graal-25.5.5`, "GraalPy3.13", published 2026-11-03);
* designed for embedding: `org.graalvm.polyglot.Context`, `GraalPyResources.contextBuilder()`,
  documented Maven/Gradle coordinates on Maven Central;
* real bidirectional interop — Python calls Java through the `java` module
  (`java.type("java.math.BigInteger")`, `from java.util import ArrayList`), Java calls Python
  through `Value`;
* pure JVM: the same jars run on Windows, macOS and Linux, on the client and on a dedicated
  server, with no per-platform native payload;
* pip-compatible package model, which the dependency packaging in
  [`dependencies.md`](dependencies.md) builds on;
* license: the `oracle/graalpython` repository ships `LICENSE.txt` = **UPL v1.0** (permissive).
  `[UNVERIFIED-HERE]` the license texts *inside* the published Maven artifacts could not be
  downloaded in this environment (Maven Central is not reachable); the build copies whatever
  license files are present in the shaded jars into `META-INF/licenses/` and
  `THIRD_PARTY_LICENSES.md` lists what must be preserved.

Costs, stated honestly:

* **Size.** A shaded GraalPy runtime is large (the language jar, Truffle, ICU data). The exact
  byte size could not be measured here — Maven Central is unreachable in this sandbox.
  `[UNVERIFIED-HERE]`
* **Startup/memory.** Creating a context costs time and heap; we create one context per
  Python mod (see §6) and start them lazily.
* **Performance.** On a stock OpenJDK Truffle runs Python in the interpreter (no runtime
  compiler), so `engine.WarnInterpreterOnly` is silenced deliberately. Python mod code must
  not be written for per-frame hot loops.
* **Native Python extensions** (C modules such as numpy binaries) are out of scope; only
  pure-Python wheels are supported.

---

## 4. Component model (client vs server-capable)

Three artifacts per (loader × Minecraft) pair. They never share classes, so installing more
than one cannot produce duplicate classes on a class loader.

| Artifact | Mod id | Fabric `environment` / NeoForge type | Contents | Needed when |
|---|---|---|---|---|
| `pythonforminecraft-core-<loader>-<mc>-<v>.jar` | `pythonforminecraft_core` (Fabric mod with **no** entry points) / jar with `FMLModType: LIBRARY` (NeoForge, plugin layer) | `*` / LIBRARY | loader-agnostic core + shaded GraalPy + the `pfm` Python package + language adapter (Fabric) / `IModLanguageLoader` service (NeoForge). **No client classes.** | always |
| `pythonforminecraft-client-<loader>-<mc>-<v>.jar` | `pythonforminecraft` | `client` / NeoForge mod with `Dist` guards | client bootstrap: client entry points, client events, client handles | the instance is a client |
| `pythonforminecraft-server-<loader>-<mc>-<v>.jar` | `pythonforminecraft_server` | `*` / NeoForge mod | common + dedicated-server bootstrap: common/server entry points, server events, server handles, command registration | Python code must run on a dedicated server |

Rules this enforces:

* a **client-only** Python mod needs *core + client* on the client and **nothing** on the
  server — the core jar carries no client classes and its Fabric environment is `*`, so even
  if it is present on a server it stays inert;
* a **server** Python mod needs *core + server* on the server; the client jar is not required
  and must not be installed there;
* client classes live only in the client artifact, so a dedicated server never loads them
  (Fabric skips `environment: client` mods entirely; on NeoForge the client jar is simply not
  installed, and everything inside it is `Dist`-guarded);
* the client artifact never claims to execute Python on a server. If only *core + client* are
  installed, Python runs on the client only.

Why three and not two: a two-artifact split would either duplicate the core classes between
the client and server jars (the failure mode the brief forbids) or make one jar's classes
depend on a jar that is intentionally absent on one side.

---

## 5. Python mod format

A Python mod is a normal mod jar. Its own metadata is the loader's; Python-for-Minecraft adds
one loader-specific piece.

### Fabric (`fabric.mod.json`)

```json
{
  "schemaVersion": 1,
  "id": "pyhello_client",
  "version": "1.0.0",
  "environment": "client",
  "entrypoints": {
    "client": [ { "adapter": "python", "value": "pyhello_client.entry:PyHelloClient" } ]
  },
  "custom": {
    "pythonforminecraft": {
      "python_root": "python",
      "vendor": ["python/vendor"],
      "modules": ["pyhello_client"]
    }
  },
  "depends": {
    "pythonforminecraft_core": ">=1.0.0",
    "pythonforminecraft": ">=1.0.0"
  }
}
```

The `python` adapter is declared by the core artifact in `languageAdapters`, exactly like FLK
declares `kotlin`.

### NeoForge (`META-INF/neoforge.mods.toml`)

```toml
modLoader = "pythonforminecraft"
loaderVersion = "[1,)"
license = "Apache-2.0"

[[mods]]
modId = "pyhello_common"
version = "1.0.0"
displayName = "PyHello Common"

[modproperties.pyhello_common]
python_root = "python"
vendor = ["python/vendor"]
modules = ["pyhello_common"]
pyfm_main = "pyhello_common.entry:PyHelloCommon"
pyfm_server = "pyhello_common.entry:PyHelloCommon"
```

`modLoader` selects our `IModLanguageLoader`; the entry points ride in
`[modproperties.<modId>]` because FML has no `entryPoint` key. **This asymmetry between the
two loaders is real and is not hidden behind a common abstraction.**

### Entrypoint notation (identical on both loaders)

`"package.module:attribute"` (console-script style):

| Attribute is | Behaviour |
|---|---|
| a callable | called with zero arguments (or with the `pfm.ModContext` if it declares one parameter) |
| a class | instantiated, then its lifecycle hooks are called |
| an object | its lifecycle hooks are called |

Lifecycle hooks: `on_initialize()` (common), `on_client_initialize()` (client),
`on_server_initialize()` (dedicated server). Events are registered with decorators, not by
hook name (`@pfm.event("server_start")`).

---

## 6. Runtime, isolation, threading

* **One `Engine` per side, one `Context` per Python mod.** Separate contexts give each mod its
  own `sys.modules`, `sys.path` and `pfm` registry, so imports and globals cannot leak between
  mods, and a mod can be torn down alone.
* **Python sources are extracted, not read from the jar.** Python files inside a mod jar are
  unpacked to `<game>/pythonforminecraft/<modId>/python` (content-hash cached) and that path is
  prepended to `sys.path`; vendored wheels are unpacked the same way. Nothing is downloaded at
  game runtime.
* **Single-threaded execution with an explicit lock.** A Truffle context is not safe for
  concurrent access, while Minecraft has a client thread and (in single player) an integrated
  server thread. Every Python call goes through `PythonRuntime.enter(...)`, which holds a
  reentrant lock and `enter()`/`leave()`s the context on the calling thread.
* **Thread expectations are documented per event** and asserted at dispatch time: server
  events run on the server thread, client events on the client thread.

## 7. Errors, shutdown, trust

* A Python failure is reported as: mod id → entry point/handler → file → line → Python
  traceback. A mod whose Python entry point throws is **not** reported as loaded: the Fabric
  adapter throws `LanguageAdapterException`, the NeoForge loader throws `ModLoadingException`,
  so the loader surfaces the failure itself.
* Shutdown: registries are cleared, every context is closed, the engine is closed. Wired to
  Fabric's client/server stopping events, NeoForge's server-stopping event and a JVM shutdown
  hook as a fallback.
* **This is not a sandbox.** Python mods get host access equivalent to the game's own JVM
  process: file system, network, `System.exit`. Only install Python mods you trust. See
  [`security.md`](security.md).

## 8. Blockers

See [`testing.md`](testing.md) §"Blockers". In short: this sandbox has no JDK, no Gradle and
no route to Maven Central / Fabric Maven / Mojang, so no JVM artifact could be compiled or
launched here. Everything JVM-side in this repository is written against signatures read from
upstream sources and is marked `[UNVERIFIED-HERE]` until built.
