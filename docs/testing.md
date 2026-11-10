# Testing record

Everything below was recorded on **2026-11-10 12:22 UTC** in the environment where this
project was written, on commit `9336bec`, branch
`arena/f8d2e234-python-for-minecraft`, Python 3.11.2, Debian 12.

**Status vocabulary** (the Russian mirror uses the exact Russian terms):

| Status | Meaning |
| --- | --- |
| passed | The command ran here and its output matched what was expected. |
| failed | The command ran here and did not produce the expected result. |
| not run | The command could have been run here and was not. There is no excuse for this cell. |
| blocked | The command cannot be run in this environment. The blocker is named in the same row. |

The distinction matters: "blocked" is a statement about the sandbox, not about the code. A
blocked cell is **not** a pass, and no blocked cell has been converted into a pass anywhere
in this repository.

## 1. What this environment could and could not do

| Capability | State | Evidence |
| --- | --- | --- |
| Python 3.11 | available | `python3 --version` → `Python 3.11.2` |
| JDK / `javac` | **absent** | `ls /usr/lib/jvm` → `No such file or directory`; `find / -maxdepth 4 -name javac` → no results |
| Installing a JDK | **impossible** | `apt-get update` → `Acquire (13: Permission denied)`. Adoptium publishes its JDK in GitHub releases, but release assets are served from `objects.githubusercontent.com`, which returns HTTP `000` (connection failure) here. |
| Gradle | **absent** | no `gradle` on `PATH` |
| Maven Central | **unreachable** | `curl -I https://repo1.maven.org/maven2/org/slf4j/slf4j-api/2.0.17/slf4j-api-2.0.17.jar` → HTTP `000` |
| `maven.fabricmc.net`, `piston-meta.mojang.com` | **unreachable** | `SSL_ERROR_SYSCALL` on both |
| GitHub API / raw, npmjs, PyPI | reachable | used to verify loader SPI signatures, versions and licences |
| Display / Minecraft licence / Minecraft account | **absent** | no X server, no licence, no credentials |

Consequence, stated once and applied to every row below: **no Java code in this repository
has ever been compiled, no Gradle build has ever run, and neither the Minecraft client nor a
dedicated server has ever been launched.** Where a row says "blocked", that is why.

## 2. Checks that really ran (loader-independent)

| # | Combination | Component checked | Check | Command | Exact result | Status | Blocker / note | Evidence |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A1 | all four | `python/pfm` + `python/tests` | Unit tests for the public API, protocol, entrypoints, events, commands, isolation, tracebacks, shutdown | `cd python && python3 -m unittest discover -s tests -t .` | `Ran 92 tests in 0.032s` / `OK` | passed | — | this file, §2 |
| A2 | all four | `tools/vendor_deps.py` | Reproducible vendoring of a real wheel, with hash verification | `python3 tools/vendor_deps.py --check --requirements examples/pyhello-common/requirements.txt --out examples/pyhello-common/python/vendor` | `ok: six 1.17.0 (wheel sha256 4721f391ed90541fddacab5acf947aa0d3dc7d27b2e1e8eda2be8970586c3274)` | passed | The wheel was genuinely downloaded from PyPI and unpacked into the repository, not simulated | `examples/pyhello-common/python/vendor/VENDOR.lock.json` |
| A3 | all four | 10 `fabric.mod.json`, 8 `neoforge.mods.toml`, 2 service files | Mod metadata, mod ids, entrypoint→Python resolution, component dependencies | `python3 tools/validate_metadata.py` | `PASSED: 30 checks, no problems` | passed | — | this file, §2 |
| A4 | all four | `tools/validate_metadata.py` | Negative self-test: the validator must reject broken metadata | `python3 tools/validate_metadata.py --self-test` | `SELF-TEST PASSED: 4/4 broken cases rejected` | passed | Proves A3 is not vacuous | this file, §2 |
| A5 | all four | 34 `.java` files (33 types) | Imports resolve, file/type names agree, brackets balance, own-type call sites hit declared members | `python3 tools/check_java.py` | `PASSED: no problems in 34 files / 33 types` (271 member checks, 3 warnings about `getMessage()` inherited from `RuntimeException`) | passed | This is **not** a compile. It cannot see JDK, Truffle, Fabric or NeoForge types | this file, §2 |
| A6 | all four | `tools/check_java.py` | Negative test: rename `PythonRuntime.create` → `make` and confirm the check fails | `sed -i 's/public static PythonRuntime create(/public static PythonRuntime make(/' core/…/PythonRuntime.java && python3 tools/check_java.py` | `FAILED: 2 problem(s)` — both adapter call sites reported, then the file was restored | passed | Proves A5 is not vacuous | this file, §2 |

## 3. Per-combination matrix

The four combinations are **not** interchangeable: Fabric 1.21.1 uses the
`net.fabricmc.fabric-loom-remap` plugin with Mojang mappings and `modImplementation`,
Fabric 26.3 uses `net.fabricmc.fabric-loom` with no mappings and plain `implementation`, and
the two NeoForge combinations use ModDevGradle on a different Gradle line. Each row is
therefore listed separately.

Status of every build/launch row below: **blocked**, for the same named reason — no JDK and
no Maven Central. They are listed individually so that nothing is hidden behind a single
"everything is blocked" sentence, and so that CI can fill each cell in separately.

| # | Combination | Component checked | Check | Command | Exact result | Status | Blocker / note | Evidence |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| B1 | Fabric + MC 1.21.1 | `pyfm-core` + `pyfm-client` | Clean client build | `cd platforms/fabric-1.21.1 && gradle build` | not attempted | blocked | no JDK, no `repo1.maven.org`, no `maven.fabricmc.net` | CI job `fabric-1.21.1` |
| B2 | Fabric + MC 1.21.1 | `pyfm-core` + `pyfm-server` | Server-capable build | same project, `pyfm-server` subproject | not attempted | blocked | as B1 | CI job `fabric-1.21.1` |
| B3 | Fabric + MC 1.21.1 | `pyhello_client`, `pyhello_common` | Test-mod build | `cd examples/pyhello-*/fabric-1.21.1 && gradle build` | not attempted | blocked | as B1 | CI job `fabric-1.21.1` |
| B4 | Fabric + MC 1.21.1 | produced jars | jar metadata / mod id / dependency check | `jar tf`, inspect `fabric.mod.json` inside the jar | not attempted | blocked | as B1 | CI job `fabric-1.21.1` |
| B5 | Fabric + MC 1.21.1 | Minecraft client | Client launch | `gradle runClient` | not attempted | blocked | no JDK, no licence, no display, no Minecraft assets | — |
| B6 | Fabric + MC 1.21.1 | Dedicated server | Server launch | `gradle runServer` | not attempted | blocked | no JDK, EULA not accepted (the project does not accept it on the owner's behalf) | CI job `launch`, opt-in |
| B7 | Fabric + MC 1.21.1 | game log | Log-marker smoke test (`[pyhello-common]`) | grep of the launch log | not attempted | blocked | depends on B5/B6 | — |
| B8 | NeoForge + MC 1.21.1 | `pyfm-core` + `pyfm-client` | Clean client build | `cd platforms/neoforge-1.21.1 && gradle build` | not attempted | blocked | no JDK, no `repo1.maven.org`, no `maven.neoforged.net` | CI job `neoforge-1.21.1` |
| B9 | NeoForge + MC 1.21.1 | `pyfm-core` + `pyfm-server` | Server-capable build | same project, `pyfm-server` subproject | not attempted | blocked | as B8 | CI job `neoforge-1.21.1` |
| B10 | NeoForge + MC 1.21.1 | `pyhello_client`, `pyhello_common` | Test-mod build | `cd examples/pyhello-*/neoforge-1.21.1 && gradle build` | not attempted | blocked | as B8 | CI job `neoforge-1.21.1` |
| B11 | NeoForge + MC 1.21.1 | produced jars | jar metadata / `FMLModType` / `neoforge.mods.toml` check | `jar tf`, `unzip -p` | not attempted | blocked | as B8 | CI job `neoforge-1.21.1` |
| B12 | NeoForge + MC 1.21.1 | Minecraft client | Client launch | `gradle runClient` | not attempted | blocked | as B5 | — |
| B13 | NeoForge + MC 1.21.1 | Dedicated server | Server launch | `gradle runServer` | not attempted | blocked | as B6 | CI job `launch`, opt-in |
| B14 | NeoForge + MC 1.21.1 | game log | Log-marker smoke test | grep of the launch log | not attempted | blocked | depends on B12/B13 | — |
| B15 | Fabric + MC 26.3 | `pyfm-core` + `pyfm-client` | Clean client build | `cd platforms/fabric-26.3 && gradle build` | not attempted | blocked | as B1; additionally this combination needs JDK 25, which is not installed | CI job `fabric-26.3` |
| B16 | Fabric + MC 26.3 | `pyfm-core` + `pyfm-server` | Server-capable build | `pyfm-server` subproject | not attempted | blocked | as B15 | CI job `fabric-26.3` |
| B17 | Fabric + MC 26.3 | example mods | Test-mod build | `cd examples/pyhello-*/fabric-26.3 && gradle build` | not attempted | blocked | as B15 | CI job `fabric-26.3` |
| B18 | Fabric + MC 26.3 | produced jars | jar metadata check | `jar tf` | not attempted | blocked | as B15 | CI job `fabric-26.3` |
| B19 | Fabric + MC 26.3 | Minecraft client | Client launch | `gradle runClient` | not attempted | blocked | as B5 | — |
| B20 | Fabric + MC 26.3 | Dedicated server | Server launch | `gradle runServer` | not attempted | blocked | as B6 | CI job `launch`, opt-in |
| B21 | Fabric + MC 26.3 | game log | Log-marker smoke test | grep of the launch log | not attempted | blocked | depends on B19/B20 | — |
| B22 | NeoForge + MC 26.3 | `pyfm-core` + `pyfm-client` | Clean client build | `cd platforms/neoforge-26.3 && gradle build` | not attempted | blocked | as B8; needs JDK 25 | CI job `neoforge-26.3` |
| B23 | NeoForge + MC 26.3 | `pyfm-core` + `pyfm-server` | Server-capable build | `pyfm-server` subproject | not attempted | blocked | as B22 | CI job `neoforge-26.3` |
| B24 | NeoForge + MC 26.3 | example mods | Test-mod build | `cd examples/pyhello-*/neoforge-26.3 && gradle build` | not attempted | blocked | as B22 | CI job `neoforge-26.3` |
| B25 | NeoForge + MC 26.3 | produced jars | jar metadata check | `jar tf`, `unzip -p` | not attempted | blocked | as B22 | CI job `neoforge-26.3` |
| B26 | NeoForge + MC 26.3 | Minecraft client | Client launch | `gradle runClient` | not attempted | blocked | as B5 | — |
| B27 | NeoForge + MC 26.3 | Dedicated server | Server launch | `gradle runServer` | not attempted | blocked | as B6 | CI job `launch`, opt-in |
| B28 | NeoForge + MC 26.3 | game log | Log-marker smoke test | grep of the launch log | not attempted | blocked | depends on B26/B27 | — |

## 4. Specific claims that are deliberately **not** made

| Claim | Reality |
| --- | --- |
| "The client-only mod was verified to work without PyFM on the server" | **Not verified.** It is *designed* for that: `pyhello_client` declares `environment: "client"` on Fabric and lives in a client-only artifact on NeoForge, and the client component is a separate jar with its own mod id, so nothing server-side requires it. Whether a dedicated server actually starts without it was never observed, because no server was ever started. |
| "A client can connect to a server with these mods" | **Not tested at all.** No claim is made about client↔server connectivity, protocol or sync. |
| "The Java code compiles" | **Unknown.** A static check passed (A5/A6). `javac` never ran. |
| "GraalPy embeds correctly and Python mods load" | **Unknown.** The Truffle API signatures were read from the `oracle/graal` sources and the code was written against them, but no `Context` was ever created here. The Python half of the protocol is tested with a fake bridge. |
| "The Shadow plugin works with Gradle 9.8.2" | **Unverified.** Recorded as a risk for the CI matrix. |
| "NeoForge 26.3 uses the event class names used in `PyFmNeoForgeServer`/`ClientHooks`" | **Unverified.** The names come from the 21.1 line; 26.x may differ. |
| "The exact ModDevGradle patch version is 2.0.90" | **Unverified.** `projects.neoforged.net` is unreachable; `2.0.90` is a placeholder marked `TODO(verify)` in `tools/gen_builds.py`. |

## 5. Known risks the first real build must check

1. `com.gradleup.shadow` 9.2.2 against Gradle 9.8.2 — if it fails, pin the 26.3 Fabric
   builds to a Gradle version the plugin supports and record the change.
2. NeoForge 26.3 event class names in the two hook classes.
3. `verifyPythonRuntime` will fail the core build if the GraalPy artifacts do not contain
   `META-INF/services/com.oracle.truffle.api.TruffleLanguage$Provider` under that exact name.
4. The Gradle wrapper jars are absent. Regenerate them with
   `gradle wrapper --gradle-version <version>` inside each build directory; CI uses
   `gradle/actions/setup-gradle` and does not need them.

## 6. How to reproduce what passed here

```sh
cd python && python3 -m unittest discover -s tests -t .     # 92 tests
python3 tools/validate_metadata.py                          # 30 checks
python3 tools/validate_metadata.py --self-test              # 4/4 rejected
python3 tools/check_java.py                                 # 34 files, 33 types
python3 tools/vendor_deps.py --check \
  --requirements examples/pyhello-common/requirements.txt \
  --out examples/pyhello-common/python/vendor               # six 1.17.0
```

All five commands are wired into `./build-all.sh` and into the `python` CI job, so they run
before any Gradle build is attempted.
