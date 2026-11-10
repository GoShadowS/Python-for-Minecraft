# Comparison with Kotlin for Forge and Fabric Language Kotlin

This table compares Python-for-Minecraft (PyFM) with the two reference projects feature by
feature. It does **not** claim parity. Several rows are explicitly "not implemented" and the
reason is given.

**Status vocabulary used in the PyFM column** (the Russian mirror uses the equivalent terms):

* **implemented and verified** — the code exists and a check that really ran proves it works.
* **partially implemented** — the code exists, but a part of it is unverified or incomplete.
* **not applicable** — the feature has no meaning for a Python language provider, with the
  reason stated.
* **not implemented** — missing, with the reason and the plan.

Nothing in this table may be read as "the whole Minecraft API is available from Python".
What Python code can reach is documented precisely in [`api.md`](api.md); the boundary is
drawn by the PyFM bridge, not by the game.

## Reference projects

| | Kotlin for Forge | Fabric Language Kotlin |
| --- | --- | --- |
| Loader | NeoForge (FancyModLoader language plugin) | Fabric |
| Mechanism | `modLoader = "kotlinforforge"` in `neoforge.mods.toml`, `loaderVersion = "[5,)"` | `"adapter": "kotlin"` in `fabric.mod.json` entrypoints, `schemaVersion: 1`, class declared under `languageAdapters` |
| Entrypoint notation | Kotlin object / `@Mod.EventBusSubscriber` classes | `"pkg.Class"`, `"pkg.FileKt::function"`, `"pkg.FileKt::field"` |
| Version seen here | 6.5.0 (branch `6.x`, min MC 1.21.9, `unsupported_mc_version = 26.4`, toolchain 25, Kotlin 2.2.20) | `1.14.2+kotlin.2.4.21` |
| Distribution | `FMLModType: LIBRARY` + `GAMELIBRARY` split, ModDevGradle `JarJar` | one jar bundling the Kotlin stdlib |
| Verified from | `thedarkcolour/KotlinForForge@6.x` README and build files, GitHub API | `FabricMC/fabric-language-kotlin` README, GitHub API |

## Feature table

| # | Feature | Kotlin for Forge /FLK behaviour | PyFM behaviour | Loader + version | How verified | Why not done / plan |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Loader-native language plugin | KFF registers `kotlinforforge`; FLK registers `kotlin` | Registers `python` (NeoForge `IModLanguageLoader` via `META-INF/services`, Fabric `LanguageAdapter` via `languageAdapters`) | Fabric 0.20.1 (1.21.1 & 26.3), NeoForge 21.1.265 / 26.3.0.100 | SPI signatures read from `FabricMC/fabric-loader@0.20.1` and `neoforged/FancyModLoader@1.21.1`/`11.x`; the service file and adapter class are cross-checked by `tools/validate_metadata.py` | — |
| 2 | Entrypoint as class, object or function | KFF: classes/objects; FLK: class, `::function`, `::field` | `package.module:Attribute` where the attribute may be a class, an instance, or a callable. Lifecycle hooks `on_initialize` / `on_client_initialize` / `on_server_initialize` | both loaders, all four combinations | 92 Python unit tests incl. entrypoint resolution for all three attribute kinds | `::field` has no Python analogue; not planned |
| 3 | Side-specific entrypoints | KFF: `DistExecutor`; FLK: `client`/`server` entrypoint keys | Fabric: `main`/`client`/`server` keys. NeoForge: `pyfm_main`/`pyfm_client`/`pyfm_server` mod properties + separate client and server jars | both | `tools/validate_metadata.py` checks the keys and that client classes are absent from the server artifact's source set | — |
| 4 | Client code never loads on a dedicated server | KFF/FLK rely on the loader's split plus `Dist` guards | Three separate artifacts: `pythonforminecraft_core` (env `*`), `pythonforminecraft` (env `client`), `pythonforminecraft_server` (env `*`, side-guarded). NeoForge client hooks live in a separate jar with a `Dist.CLIENT` guard | both | Static: `tools/check_java.py` (271 checks over 34 files) proves the client class set does not reference server-only code paths. **No dedicated-server launch was performed** | Launch verification blocked: no JDK, no Minecraft, no licence — see `testing.md` |
| 5 | One `Context`/runtime per Python mod (namespace isolation) | N/A — Kotlin shares one JVM class loader per mod file | One Truffle `Context` per Python mod; separate `sys.path`; separate `pfm.runtime` per mod id | both | 92 Python tests, incl. two fake mods with same-named modules importing different things | — |
| 6 | Java/Kotlin interop from mod code | Direct: same JVM, same types | `pfm.java.import_class("net.minecraft.…")` through a bridge; classes are reachable, but the call goes through the polyglot host-access layer | both | Python tests use a fake bridge; **no real JVM interop test ran** | Requires a compiled build; the GraalPy host-access configuration is written but unexecuted |
| 7 | Event bus | KFF: NeoForge `IEventBus`; FLK: Fabric callbacks | `pfm.event("server_start")` decorator + `pfm.dispatch()`; nine event names bridged from the loader | both | 92 Python tests covering registration, dispatch, ordering, and per-mod isolation of handlers | The event set is small on purpose; extending it needs a compiled build to test |
| 8 | Commands from mod code | KFF/FLK: vanilla Brigadier directly | `@pfm.command("name")` → bridge `register_command` → loader registers a Brigadier/`Commands.literal` node; `ctx.reply(...)` answers the source | both | Python tests cover registration, argument passing, unknown-command failure. Java side: static check only | — |
| 9 | Error reporting with mod id + file + line, without marking the mod loaded | Both rely on the loader's mod-loading failure handling | `PythonTracebacks.format` produces `[PyFM] mod <id> (<phase>): …` plus `at file:line` for guest frames; the entrypoint phase is aborted and the mod is recorded as failed, other mods still load | both | Python side: 92 tests incl. traceback formatting. Java side: static check only | Same blocker as 6 |
| 10 | Shutdown / resource release | Loader-driven `@Mod` lifecycle | `PyFmLifecycle.stop()` → `_shutdown(mod_id)` per mod → `Context.close()`, shared `Engine.close()`, extracted-file handles released | both | Python tests cover `_shutdown` ordering and double-shutdown safety | — |
| 11 | Bundling the language runtime inside the mod jar | KFF: LIBRARY + GAMELIBRARY jars, JarJar; FLK: stdlib shaded into one jar | GraalPy is shaded into `pythonforminecraft_core` with `shadowJar` + `mergeServiceFiles`, plus a `verifyPythonRuntime` task that fails the build if the Truffle service file or the `pfm` package is missing | both | Generator emits the task; **never executed** — no Gradle/Maven access | Will be verified by the CI matrix |
| 12 | Third-party Python packages | Maven deps via `JarJar` / `modImplementation` | `tools/vendor_deps.py` downloads wheels at build time, verifies the sha256, unpacks them into `python/vendor/` and writes `VENDOR.lock.json`. No downloads at game runtime | both | Really run: `six==1.17.0` vendored into `examples/pyhello-common`, `--check` passes | Only pure-Python wheels: a wheel with native extensions cannot be unpacked and used |
| 13 | Kotlin/Python standard library parity with the host language | Full Kotlin stdlib | GraalPy 3.13 stdlib, as shipped by GraalPy. PyFM deliberately does **not** re-expose the JVM stdlib as Python | both | GraalPy version pin verified (`graal-25.5.5` = GraalPy 3.13) | — |
| 14 | Kotlin reflection / annotation-driven features (`@Mod.EventBusSubscriber`, `FMLModType` tricks, coroutines) | Core to KFF's ergonomics | **Not applicable**: Python has no compile-time annotations and no coroutine scheduler bound to the game thread. PyFM exposes decorators instead | — | n/a | Not planned; would be a different product |
| 15 | Compile-time API surface / type safety | Kotlin is compiled against the loader API | **Not applicable**: Python is interpreted; there is no compile step for a mod. PyFM's API is documented and unit-tested instead | — | n/a | — |
| 16 | Sandbox / security boundary | Neither KFF nor FLK sandboxes mod code | **Not implemented, and PyFM does not claim otherwise.** Python mod code has full JVM access through the bridge; it is treated as trusted | — | Documented in `security.md` | A sandbox needs a GraalVM polyglot `SandboxPolicy` decision plus a threat model; out of scope for 1.0 |
| 17 | Debugging support (IDE attach, hot reload) | Kotlin: standard JVM debugging | **Not implemented** | — | n/a | Planned: expose the Truffle `Context` name and enable `--vm.Xdebug`-style options through config |
| 18 | Multiple loaders from one source set | KFF/FLK are single-loader by design | One `core/` + `loader-adapters/{fabric,neoforge}` tree, compiled four times by generated builds | all four | `tools/gen_builds.py` emits 12 subprojects + 8 example builds | — |
| 19 | Version-specific build configurations | Both ship one branch per MC version | Four independent Gradle projects with different plugin ids, mappings handling, dependency configurations, remapping and Java release levels | all four | Differences are encoded in `tools/gen_builds.py`; **no build ran** | — |
| 20 | Publishing coordinates (Maven, Modrinth, CurseForge) | Both publish to Maven + mod portals | **Not implemented** | — | n/a | Needs the owner's credentials and explicit permission; no release was made |

## What PyFM does not do, stated plainly

* It does not give Python code "the full Minecraft API". It gives Python code the classes
  that `pfm.java.import_class` can resolve plus the handles `pfm.mc` exposes. Registry
  access, mixins, screen rendering and datapack manipulation are *not* wrapped; they may
  work through raw Java interop but are untested and unsupported.
* It does not port the Kotlin standard library or Kotlin reflection.
* It does not claim feature parity with KFF or FLK: rows 6, 9, 11, 16, 17 and 20 are
  incomplete or absent.
* It does not sandbox anything. A Python mod can do anything the JVM can do.
