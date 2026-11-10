# Python for Minecraft

> An analogue of **"Kotlin for Forge"** and **"Fabric Language Kotlin"** for mods written in
> Python.
>
> Works with the **NeoForge** and **Fabric** loaders, for **Minecraft 1.21.1** and **26.3**.

[Русская версия](README.ru.md)

This is a **language provider**, not a bot framework and not an RCON/console tool. You write
an ordinary Minecraft mod whose entry point is Python; the loader discovers it, and
Python-for-Minecraft (PyFM) runs it inside the game's own JVM.

---

## ⚠ Read this before you use anything

This repository was written in a sandbox that has **no JDK and no access to Maven Central**.
Consequently:

* the **Python** half is implemented and tested — 92 unit tests pass here;
* the **Java** half (34 files) is written but **has never been compiled**;
* **no Gradle build has ever run** and **neither the client nor a dedicated server has ever
  been launched**;
* a client-only mod is *designed* not to need anything on the server, and that is verified
  statically, but **it was never observed at runtime**.

Every claim in this repository is tagged with how it was verified, and every blocked check is
recorded with its exact reason in [`docs/testing.md`](docs/testing.md). Nothing has been
presented as working when it was not.

---

## What it does

* Runs Python mods **in the JVM** through GraalPy 3.13 — no separate process, no network
  bridge, no external service.
* One **GraalPy context per Python mod**: separate namespaces, separate `sys.path`, one mod's
  crash does not take the others down.
* **Three artifacts per loader**: `pythonforminecraft_core` (both sides),
  `pythonforminecraft` (client), `pythonforminecraft_server` (server-capable). Client classes
  never load on a dedicated server.
* **Four independent build configurations**, because Fabric 1.21.1, Fabric 26.3, NeoForge
  1.21.1 and NeoForge 26.3 genuinely differ (different Loom plugin, mappings, dependency
  configuration, JDK and Gradle line).
* Python dependencies are **vendored at build time**, hash-locked and shipped inside the mod
  jar. Nothing is downloaded at game runtime.
* Python errors are reported with the **mod id, the phase and `at file:line`**, and a failing
  mod is not marked as loaded.

## What it does not do

It does **not** give Python "the full Minecraft API". The public surface is: nine events,
three handles (`pfm.mc.server` / `.client` / `.player`), commands, logging, and
`pfm.java.import_class(...)` for raw Java interop. There is no registry, block, item, screen,
entity or datapack API, no mixins, no networking, no hot reload, and **no sandbox** — Python
mods are trusted code with the same reach as the JVM they run in.

Full detail: [`docs/comparison.md`](docs/comparison.md) (feature-by-feature against Kotlin for
Forge and Fabric Language Kotlin) and [`docs/api.md`](docs/api.md).

## A Python mod looks like this

```python
import pfm


class MyMod:
    def on_initialize(self):
        pfm.log.info("hello from Python on the %s side" % pfm.side())


@pfm.event("player_join")
def on_player_join(event):
    pfm.log.info("player joined: %s" % event.data)


@pfm.command("myhello", usage="/myhello")
def myhello(ctx):
    ctx.reply("hello from Python")
```

and the loader finds it through ordinary mod metadata — Fabric:

```json
"entrypoints": {
    "main": [{"adapter": "python", "value": "mymod.entry:MyMod"}]
}
```

NeoForge:

```toml
modLoader = "pythonforminecraft"
[modproperties.mymod]
pyfm_main = "mymod.entry:MyMod"
```

## Repository map

| Path | What is in it |
| --- | --- |
| `python/pfm/` | the public Python package (`pfm`) — entry points, events, commands, logging, interop |
| `python/tests/` | 92 unit tests for the Python side, with a fake bridge |
| `core/` | loader-agnostic Java core (21 files): runtime, isolation, protocol, tracebacks, resources |
| `loader-adapters/fabric/` | Fabric language adapter, client and dedicated-server hooks, commands |
| `loader-adapters/neoforge/` | NeoForge `IModLanguageLoader`, mod container, client and server hooks, commands |
| `platforms/<loader>-<mc>/` | generated Gradle builds, three subprojects each |
| `examples/pyhello-client/`, `examples/pyhello-common/` | two real Python test mods for all four combinations |
| `tools/` | `vendor_deps.py`, `validate_metadata.py`, `check_java.py`, `gen_builds.py`, `gen_examples.py` |
| `docs/` | architecture, API, authoring, installation, dependencies, security, testing, comparison |

## Documentation

| Document | English | Русский |
| --- | --- | --- |
| Architecture and runtime choice | [docs/architecture.md](docs/architecture.md) | [docs/architecture.ru.md](docs/architecture.ru.md) |
| Public API, entry points, events | [docs/api.md](docs/api.md) | [docs/api.ru.md](docs/api.ru.md) |
| Writing and building a Python mod | [docs/authoring.md](docs/authoring.md) | [docs/authoring.ru.md](docs/authoring.ru.md) |
| Loader / version / side matrix, installation | [docs/installation.md](docs/installation.md) | [docs/installation.ru.md](docs/installation.ru.md) |
| Packaging Python dependencies | [docs/dependencies.md](docs/dependencies.md) | [docs/dependencies.ru.md](docs/dependencies.ru.md) |
| Trust, security, permissions | [docs/security.md](docs/security.md) | [docs/security.ru.md](docs/security.ru.md) |
| Testing record | [docs/testing.md](docs/testing.md) | [docs/testing.ru.md](docs/testing.ru.md) |
| Comparison with the reference projects | [docs/comparison.md](docs/comparison.md) | [docs/comparison.ru.md](docs/comparison.ru.md) |
| Troubleshooting and limitations | [docs/troubleshooting.md](docs/troubleshooting.md) | [docs/troubleshooting.ru.md](docs/troubleshooting.ru.md) |
| Primary sources | [docs/sources.md](docs/sources.md) | [docs/sources.ru.md](docs/sources.ru.md) |

## Verifying it yourself

The checks that need no JDK run anywhere:

```sh
cd python && python3 -m unittest discover -s tests -t .   # Ran 92 tests ... OK
python3 tools/validate_metadata.py                        # PASSED: 30 checks
python3 tools/validate_metadata.py --self-test            # SELF-TEST PASSED: 4/4
python3 tools/check_java.py                               # PASSED: 34 files / 33 types
python3 tools/vendor_deps.py --check \
  --requirements examples/pyhello-common/requirements.txt \
  --out examples/pyhello-common/python/vendor             # ok: six 1.17.0
```

Everything else — Gradle builds, jar inspection, launches, log markers — needs JDK 21 **and**
25 plus network access to the modding mavens and to Mojang. `./build-all.sh` runs it all, and
`.github/workflows/ci.yml` has a four-combination matrix for it. Neither has been executed by
this project.

## Licence

Apache-2.0 — see [`LICENSE`](LICENSE) and [`NOTICE`](NOTICE). Third-party licences, including
GraalPy and Truffle (UPL 1.0), are listed in
[`THIRD_PARTY_LICENSES.md`](THIRD_PARTY_LICENSES.md), with how each one was established.

`NOTICE` currently names a collective copyright holder because the repository owner has not
stated a legal name; that line must be corrected before any release.
