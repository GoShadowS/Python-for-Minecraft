# Troubleshooting and limitations

Every diagnostic shape quoted here comes from the code in this repository. Where a symptom
could not be reproduced because nothing was ever launched, that is stated rather than
invented.

## 1. Reading the log

All Python-for-Minecraft output is prefixed `[PyFM]`. Grep for it first:

```sh
grep '\[PyFM\]' logs/latest.log
```

A failing Python mod produces:

```
[PyFM] Python mod 'pyhello_common' failed during server_initialize
  at python/pyhello_common/entry.py:27
  Traceback (most recent call last):
    File "python/pyhello_common/entry.py", line 27, in on_server_initialize
      raise RuntimeError("boom")
  RuntimeError: boom
```

The mod id, the phase and the `at file:line` frame are always present. A host (Java)
exception instead ends with `host exception: <class>: <message>`.

## 2. Symptoms

| Symptom | Likely cause | What to do |
| --- | --- | --- |
| Loader says a required mod is missing: `pythonforminecraft_core` | the core jar is not in `mods/`, or it is the jar for a different loader/Minecraft combination | install the core jar that matches your loader **and** version; the artifacts are not interchangeable |
| `environment: client` mod missing on a dedicated server | working as intended | a client-only Python mod must not be installed on the server. Nothing is broken |
| `modLoader "pythonforminecraft" not found` (NeoForge) | the core jar is missing or lacks `FMLModType: LIBRARY` | reinstall the core jar; `unzip -p <core.jar> META-INF/MANIFEST.MF` must show `FMLModType: LIBRARY` |
| `No language adapter named 'python'` (Fabric) | the core jar is missing or does not declare `languageAdapters.python` | reinstall the core jar; check `fabric.mod.json` inside it |
| Entrypoint error naming `package.module:Attribute` | typo, or the module is not inside the jar, or the attribute does not exist | run `python3 tools/validate_metadata.py`; then `unzip -l <yourmod.jar> \| grep python/` to confirm the code is actually packaged |
| `no current Python mod; pfm.event()/pfm.command() can only be used while Python-for-Minecraft is initialising a mod` | `pfm.event`/`pfm.command` used at import time outside a mod runtime, or from a helper imported by two mods | only decorate at module import inside your own package, or pass `mod_id` explicitly |
| `ModuleNotFoundError` for a vendored package | `python/vendor` was not copied into the jar, or the metadata does not declare it | check `custom.pythonforminecraft.vendor` (Fabric) / `vendor` under `[modproperties]` (NeoForge), and that `processResources` copies `vendor/**` |
| `ImportError` inside a package with a compiled extension | not supported at all | see [`dependencies.md`](dependencies.md) §4. Pure-Python wheels only |
| Python `print()` output missing | stdout is routed into the game log through `PyFmLogStream` | look for the text without the `[PyFM]` prefix; prefer `pfm.log` |
| Stale Python code after an update | extracted sources are cached with a marker file | delete `<game>/pythonforminecraft/<modId>/` (marker `.pyfm-extracted`) and `<game>/pythonforminecraft/runtime/` (marker `.pyfm-runtime`); they are regenerated |
| `verifyPythonRuntime` fails the core build | the shaded jar lost the Truffle service registration or the `pfm` package | check that `mergeServiceFiles()` is still applied and that `processResources` copies `python/pfm/**` into `pythonforminecraft/` |
| Python code seems very slow | GraalPy without a Graal compiler falls back to the interpreter | expected on a stock JVM. `engine.WarnInterpreterOnly` is silenced by PyFM, so there is no warning — only the speed difference |
| `python.allowAllAccess=false` breaks a mod | host access was withdrawn, so interop stops working | this mode is unverified; see [`security.md`](security.md) §3 |

## 3. Files PyFM creates at runtime

| Path (relative to the game directory) | Purpose | Marker |
| --- | --- | --- |
| `config/pythonforminecraft.properties` | optional configuration | — |
| `pythonforminecraft/<modId>/<hash>/` | the mod's Python sources, unpacked from its jar | `.pyfm-extracted` |
| `pythonforminecraft/runtime/<version>/` | the `pfm` package, unpacked from the core jar | `.pyfm-runtime` |

The hash in the first path is derived from the mod's origin, so two different jars of the
same mod id do not share a directory. Deleting these directories is always safe; they are
regenerated at start-up.

## 4. Known limitations

* **Nothing was launched.** No client, no dedicated server, no client↔server connection.
  See [`testing.md`](testing.md).
* **No Java compilation happened here.** The Java tree passed a static consistency check, not
  `javac`.
* **The Minecraft API is not wrapped.** Nine events, three handles, one interop entry point
  and commands. There is no registry, block, item, screen, entity or datapack API.
* **Nine events only.** No render events, no lifecycle granularity beyond what
  [`api.md`](api.md) §2 lists.
* **No networking.** PyFM implements no payloads, no channels, no sync. A client and a
  server both running Python mods do not talk to each other through PyFM.
* **No sandbox.** Python mods are trusted code ([`security.md`](security.md)).
* **No hot reload, no debugger integration, no IDE support.**
* **Pure-Python wheels only** for third-party packages.
* **ModDevGradle's exact patch version is a placeholder** marked `TODO(verify)` in
  `tools/gen_builds.py`; `projects.neoforged.net` was unreachable.
* **NeoForge 26.3 event class names are unverified**; the names used come from the 21.1 line.
* **Shadow plugin vs Gradle 9.8.2 is unverified.**

## 5. Reporting a problem

Include, in this order:

1. the loader and Minecraft version, and which of the four combinations you are on;
2. which of the three PyFM jars are installed, with their exact file names;
3. the full `[PyFM]` section of `logs/latest.log`;
4. the output of `python3 tools/validate_metadata.py` run in your mod project.
