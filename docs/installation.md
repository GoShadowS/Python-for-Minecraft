# Loader / version / side matrix and installation

## 1. Supported combinations

| # | Loader | Minecraft | Java | Loader version | Metadata file | Gradle plugin | Gradle |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Fabric | 1.21.1 | 21 | Fabric Loader `0.20.1` | `fabric.mod.json` (schema 1) | `net.fabricmc.fabric-loom-remap` (Loom `1.19`) + Mojang mappings | 9.8.2 |
| 2 | NeoForge | 1.21.1 | 21 | NeoForge `21.1.265` | `META-INF/neoforge.mods.toml` | `net.neoforged.moddevgradle` | 8.14.5 |
| 3 | Fabric | 26.3 | **25** | Fabric Loader `0.20.1` | `fabric.mod.json` (schema 1) | `net.fabricmc.fabric-loom` (Loom `1.19`), **no mappings** | 9.8.2 |
| 4 | NeoForge | 26.3 | **25** | NeoForge `26.3.0.100` | `META-INF/neoforge.mods.toml` | `net.neoforged.moddevgradle` | 8.14.5 |

Facts behind this table were checked against primary sources and are recorded in
[`sources.md`](sources.md). Minecraft 26.3 is unobfuscated, which is why combinations 1 and
3 use *different* Fabric Loom plugins, different dependency configurations and different
final jar tasks: **one Gradle configuration cannot serve both**, and the artifacts of one
combination are not usable on another.

## 2. The three artifacts

Every (loader × Minecraft) combination produces three jars with different mod ids. They
never share classes, so installing two of them cannot cause duplicate-class conflicts.

| Jar | Mod id | Side | Contents | Required when |
| --- | --- | --- | --- | --- |
| `pythonforminecraft-core-<loader>-<mc>-1.0.0-all.jar` | `pythonforminecraft_core` | `*` (both) | loader-agnostic core, shaded GraalPy runtime, the `pfm` Python package, the Fabric language adapter / the NeoForge `IModLanguageLoader` service. **No client classes.** | always |
| `pythonforminecraft-client-<loader>-<mc>-1.0.0.jar` | `pythonforminecraft` | `client` | client bootstrap, client events, client handles | the instance is a client |
| `pythonforminecraft-server-<loader>-<mc>-1.0.0.jar` | `pythonforminecraft_server` | `*`, side-guarded | common + dedicated-server bootstrap, server events, server handles, command registration | Python code must run on a dedicated server |

On NeoForge the core jar is a plugin-layer library (`FMLModType: LIBRARY` in its manifest,
no `neoforge.mods.toml`); the client and server jars are normal mods.

## 3. What to install

| Situation | Client `mods/` | Server `mods/` |
| --- | --- | --- |
| Client-only Python mod | core + client + the mod | **nothing** |
| Common / server Python mod, single player | core + client + the mod | — |
| Common / server Python mod, multiplayer | core + client + the mod | core + server + the mod |
| Server-only Python mod | — | core + server + the mod |

Guarantees this gives, and the one it does not:

* **Client-only Python mods need nothing on the server.** The client component is a separate
  jar with its own mod id, and on Fabric a client-only mod declares `environment: "client"`
  so the loader never loads it server-side. The core jar has no client classes at all, so
  even if it is present on a server it stays inert.
  *Honest caveat:* this is by construction, and it is verified statically
  (`tools/validate_metadata.py` checks the environment and the source sets,
  `tools/check_java.py` checks that client and server code do not cross-reference). **No
  dedicated server was ever started here**, so the claim has not been observed at runtime.
* **Client classes never load on a dedicated server.** On Fabric they are in an
  `environment: "client"` jar; on NeoForge they are in a jar you simply do not install, and
  everything inside it is additionally `Dist.CLIENT`-guarded.
* **The client artifact never pretends to be a server runtime.** If only core + client are
  installed, Python runs on the client and nothing else.
* Not guaranteed: any client↔server interaction. PyFM implements no networking, no sync and
  no protocol. Nothing here has been tested by connecting a client to a server.

## 4. Installing

1. Pick the row in §1 that matches your game.
2. Download or build the three jars for that row. **They are not interchangeable with
   another row.**
3. Copy the jars from §3 into the instance's `mods/` directory.
4. Copy your Python mod jar into the same directory.
5. Start the game and look for `[PyFM]` in the log.

## 5. Building it yourself

```sh
./build-all.sh                       # all four combinations
./build-all.sh fabric-1.21.1         # one combination
cd platforms/neoforge-26.3 && gradle build
```

Requirements: JDK 21 **and** JDK 25 (each combination uses a toolchain), Gradle, and network
access to Maven Central, `maven.fabricmc.net`, `maven.neoforged.net` and
`piston-meta.mojang.com`.

The Gradle wrapper jars are **not** committed: they could not be downloaded in the
environment this repository was prepared in. Regenerate them per build directory with
`gradle wrapper --gradle-version 9.8.2` (Fabric) or `--gradle-version 8.14.5` (NeoForge).
CI uses `gradle/actions/setup-gradle` and does not need them.

**No build has been executed by this project.** Every build cell in
[`testing.md`](testing.md) is marked *blocked*, with the reason.
