# Writing and building a Python mod

A Python mod is an ordinary mod jar. It has its own mod id, its own metadata, its own
entry point and its own Python code. It depends on Python-for-Minecraft the same way a Java
mod depends on a library — through the loader's dependency mechanism, not through a build
plugin.

This guide is based on the two example mods in `examples/`, which are real projects with
their own metadata and build files. Read them alongside this page.

## 1. Choose what your mod is

| Your mod | Install on the client | Install on a dedicated server |
| --- | --- | --- |
| client-only (HUD, screens, keybinds) | `pythonforminecraft_core` + `pythonforminecraft` | nothing |
| common / server logic | `pythonforminecraft_core` + `pythonforminecraft` | `pythonforminecraft_core` + `pythonforminecraft_server` |

See [`installation.md`](installation.md) for the full matrix. A client-only Python mod never
requires anything on the server: the core jar has no client classes and the client component
is a separate jar with its own mod id.

## 2. Layout

```
mymod/
├── fabric-1.21.1/            # one Gradle project per supported combination
│   ├── build.gradle.kts
│   ├── gradle.properties
│   ├── settings.gradle.kts
│   └── src/main/resources/fabric.mod.json
├── neoforge-1.21.1/
│   └── src/main/resources/META-INF/neoforge.mods.toml
└── python/                   # shared between all combinations
    ├── mymod/
    │   ├── __init__.py
    │   └── entry.py
    └── vendor/               # optional, produced by tools/vendor_deps.py
```

The Python source is shared; only the metadata and the build differ per combination. There
is no reason to duplicate the Python code per loader.

A Python mod has **no Java sources**. The example builds say so explicitly
(`java.setSrcDirs(emptyList<String>())`); that keeps the jar free of accidentally compiled
Java classes.

## 3. The entry point

`python/mymod/entry.py`:

```python
import pfm

MARKER = "[mymod]"


class MyMod:
    """Instantiated once by Python-for-Minecraft; the instance lives for the whole run."""

    def on_initialize(self):
        pfm.log.info("%s common init on the %s side" % (MARKER, pfm.side()))

    def on_client_initialize(self):
        pfm.log.info("%s client init" % MARKER)

    def on_server_initialize(self):
        pfm.log.info("%s dedicated-server init" % MARKER)


@pfm.event("player_join")
def on_player_join(event):
    pfm.log.info("%s player joined: %s" % (MARKER, event.data))


@pfm.command("myhello", usage="/myhello", permission=0)
def myhello(ctx):
    ctx.reply("%s hello from Python" % MARKER)
```

The entry point is referenced as `package.module:Attribute`, here `mymod.entry:MyMod`. The
attribute may be a class, an instance, or a callable; see [`api.md`](api.md#1-entry-points).

### Fabric: `fabric.mod.json`

```json
{
    "schemaVersion": 1,
    "id": "mymod",
    "version": "${version}",
    "name": "My Mod",
    "environment": "*",
    "license": "Apache-2.0",
    "entrypoints": {
        "main": [
            {"adapter": "python", "value": "mymod.entry:MyMod"}
        ],
        "server": [
            {"adapter": "python", "value": "mymod.entry:MyMod"}
        ]
    },
    "custom": {
        "pythonforminecraft": {
            "python_root": "python",
            "modules": ["mymod"],
            "vendor": ["python/vendor"]
        }
    },
    "depends": {
        "pythonforminecraft_core": ">=1.0.0",
        "pythonforminecraft_server": ">=1.0.0",
        "fabricloader": ">=0.20.1",
        "minecraft": "~1.21.1",
        "java": ">=21"
    }
}
```

* `environment` must be `"client"` for a client-only mod. Fabric then never loads it on a
  dedicated server.
* use `main` for common code, `client` for client-only code, `server` for dedicated-server
  code.
* depend on `pythonforminecraft` for a client-only mod, on `pythonforminecraft_server` for
  common/server code. Both also need `pythonforminecraft_core`.

### NeoForge: `META-INF/neoforge.mods.toml`

```toml
modLoader = "pythonforminecraft"
loaderVersion = "[1,)"
license = "Apache-2.0"

[[mods]]
modId = "mymod"
version = "${version}"
displayName = "My Mod"
description = "A Python mod."

[[dependencies.mymod]]
modId = "neoforge"
type = "required"
versionRange = "[21.1,)"
ordering = "NONE"
side = "BOTH"

[[dependencies.mymod]]
modId = "pythonforminecraft_server"
type = "required"
versionRange = "[1.0.0,)"
ordering = "AFTER"
side = "BOTH"

[modproperties.mymod]
python_root = "python"
modules = ["mymod"]
vendor = ["python/vendor"]
pyfm_main = "mymod.entry:MyMod"
pyfm_server = "mymod.entry:MyMod"
```

NeoForge has **no** `fabric.mod.json`-style adapter key and **no** `entryPoint` key. Entry
points are passed as mod properties (`pyfm_main`, `pyfm_client`, `pyfm_server`) and read
through `IModInfo#getModProperties()`. Side separation is done with separate jars, because
`neoforge.mods.toml` has no `clientOnly`/`serverOnly` flag. This difference is real and is
not hidden by PyFM.

## 4. Building

Each combination is its own Gradle build, because the four combinations genuinely differ:

| | Fabric 1.21.1 | Fabric 26.3 | NeoForge 1.21.1 | NeoForge 26.3 |
| --- | --- | --- | --- | --- |
| Gradle plugin | `net.fabricmc.fabric-loom-remap` | `net.fabricmc.fabric-loom` | `net.neoforged.moddevgradle` | `net.neoforged.moddevgradle` |
| mappings | `loom.officialMojangMappings()` | none | n/a | n/a |
| dependency config | `modImplementation` | `implementation` | `neoForge` | `neoForge` |
| JDK | 21 | 25 | 21 | 25 |
| Gradle line | 9.8.2 | 9.8.2 | 8.14.5 | 8.14.5 |

```sh
cd examples/pyhello-common/fabric-1.21.1 && gradle build
```

**These builds have never been run** — the environment this project was written in has no
JDK and no Maven Central access. See [`testing.md`](testing.md). The generated build files
are in the repository so they can be run as soon as the toolchain is available.

`build.gradle.kts` must copy the Python code into the jar:

```kotlin
tasks.processResources {
    from("../python") { include("mymod/**"); into("python") }
    from("../python") { include("vendor/**"); into("python") }
    filesMatching("fabric.mod.json") { expand("version" to project.version.toString()) }
}
```

## 5. Third-party packages

See [`dependencies.md`](dependencies.md). Short version: pin and hash-lock them in
`requirements.txt`, run `tools/vendor_deps.py`, commit `python/vendor/`. Nothing is
downloaded while the game runs.

## 6. Checking your mod before you ship it

```sh
python3 tools/validate_metadata.py
```

This resolves every entry point against the Python sources, checks the mod id, the
environment, the dependency on the right PyFM component, and that declared modules and
vendor directories exist. It is the cheapest way to catch a typo that would otherwise only
appear in a crash log at start-up.

## 7. Rules that are not optional

* Log markers: give your mod a stable prefix (the examples use `[pyhello-common]`) so its
  output can be grepped out of a large log.
* Do not import another Python mod's modules. Each mod has its own runtime and its own
  `sys.path`; cross-imports only work by accident.
* Do not keep references to game objects across a server restart; `pfm` releases the
  runtime on shutdown.
* Your mod's Python code is trusted and unsandboxed. Do not load untrusted Python. See
  [`security.md`](security.md).
