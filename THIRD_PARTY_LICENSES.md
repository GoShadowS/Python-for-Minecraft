# Third-party licences

Every entry below states how the licence was established. Where the source could not be
reached from the environment the project was prepared in, that is written down instead of
guessing — the authoritative text is always the licence file inside the jar that is
actually shipped.

## Bundled into the `pythonforminecraft_core` jar

| Component | Coordinates | Licence | How established |
| --- | --- | --- | --- |
| GraalPy (the Python language) | `org.graalvm.polyglot:python-community` | UPL 1.0 | `oracle/graalpython@master:LICENSE.txt` — "This particular copy of the software is released under Universal Permissive License (UPL) v. 1.0." (3891 bytes, read through the GitHub contents API) |
| Truffle framework | `org.graalvm.polyglot:polyglot` and the Truffle runtime | UPL 1.0 | `oracle/graal@master:truffle/LICENSE.md` — "The Universal Permissive License (UPL), Version 1.0", © 2019, 2025 Oracle |
| SLF4J API | `org.slf4j:slf4j-api` | MIT | `qos-ch/slf4j` repository metadata: `spdx_id = MIT` |
| Python standard library | shipped inside the GraalPy artifacts | PSF-2.0 and the per-module licences the CPython distribution carries | Not re-verified here; GraalPy's own distribution ships the CPython licence text |
| ICU4J / Bouncy Castle and other transitive dependencies of the GraalPy artifacts | pulled in by the Gradle build | not verified in this environment | **Open item.** Maven Central was unreachable, so the transitive set could not be enumerated. The `shadowJar` task merges `META-INF/services` but does not merge licence files, so the licence texts of the shaded dependencies must be collected when the first real build runs. |

## Referenced but not bundled

| Component | Licence | How established |
| --- | --- | --- |
| Fabric Loader (`net.fabricmc:fabric-loader`) | Apache-2.0 | `FabricMC/fabric-loader` repository metadata: `spdx_id = Apache-2.0` |
| Fabric API (`net.fabricmc.fabric-api:fabric-api`) | Apache-2.0 | `FabricMC/fabric-api` repository metadata (the former `FabricMC/fabric` repository redirects to it): `spdx_id = Apache-2.0` |
| NeoForge (`net.neoforged:neoforge`) | LGPL-2.1 | `neoforged/NeoForge` repository metadata: `spdx_id = LGPL-2.1` |
| FancyModLoader (the mod-loading SPI PyFM implements) | LGPL-2.1 | `neoforged/FancyModLoader@1.21.1:LICENSE.txt` — "Minecraft Forge, Forge Mod Loader, and all parts herein are licensed under the terms of the LGPL 2.1" (27732 bytes) |
| Minecraft | proprietary | Used at compile time only, through the loader's own toolchain. Not redistributed by this project. |
| Fabric Language Kotlin | Apache-2.0 | `FabricMC/fabric-language-kotlin` — studied as the design reference, no code taken from it |
| Kotlin for Forge | LGPL-3.0 | `thedarkcolour/KotlinForForge@6.x` — studied as the design reference, no code taken from it |

## Vendored into example mods

| Component | Version | Licence | How established |
| --- | --- | --- | --- |
| `six` | 1.17.0 | MIT | Read from the wheel that `tools/vendor_deps.py` downloaded and unpacked: `examples/pyhello-common/python/vendor/six-1.17.0.dist-info/METADATA` declares `License: MIT`, © 2010-2024 Benjamin Peterson |

## Why Apache-2.0 is a workable choice for this project

* UPL 1.0 and MIT are permissive and compatible with Apache-2.0: bundling GraalPy, Truffle
  and SLF4J inside an Apache-2.0 jar keeps their notices, which is what `NOTICE` and this
  file do.
* Fabric Loader and Fabric API are Apache-2.0, so the Fabric side is licence-identical.
* LGPL-2.1 (NeoForge) is satisfied because PyFM only *links against* NeoForge at runtime and
  is distributed separately; no NeoForge code is copied into any PyFM artifact. The NeoForge
  artifacts declare LGPL-2.1 in their own `neoforge.mods.toml`-adjacent metadata, and the
  loader itself is loaded by the game, not repackaged.
* Python mods written *for* PyFM are the authors' own work; they link against the small
  public `pfm` API and are not derivative works of PyFM's implementation. This is stated in
  `docs/authoring.md` so mod authors do not have to guess.

## Open items that must be closed before a release

1. Enumerate the full transitive dependency set of the GraalPy artifacts and copy their
   licence texts into the core jar (or into this file). Requires Maven Central.
2. Replace the collective copyright holder in `NOTICE` with the real legal name.
3. Confirm the licence of every Python package a real user vendors with
   `tools/vendor_deps.py`; the tool records a wheel hash but cannot judge a licence.
