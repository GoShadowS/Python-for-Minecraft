# Packaging Python dependencies

Python mods may use third-party packages. They are **vendored at build time and shipped
inside the mod jar**. Nothing is downloaded while the game runs — no `pip`, no network, no
first-launch fetch. This is a hard rule, because a game must start identically offline and
because a silent download at start-up is not reproducible.

The tool is [`tools/vendor_deps.py`](../tools/vendor_deps.py). It was really run against
PyPI to produce `examples/pyhello-common/python/vendor/`.

## 1. Declare dependencies

`requirements.txt`, pinned and hash-locked exactly like a
`pip install --require-hashes` file:

```
six==1.17.0 \
    --hash=sha256:4721f391ed90541fddacab5acf947aa0d3dc7d27b2e1e8eda2be8970586c3274
```

No hashes → the tool refuses to run. Unpinned versions → the tool refuses to run. That is
deliberate: a build that resolves a floating version is not reproducible.

## 2. Vendor them

```sh
python3 tools/vendor_deps.py \
    --requirements examples/pyhello-common/requirements.txt \
    --out examples/pyhello-common/python/vendor
```

What it does:

1. downloads each wheel with `pip download --no-deps --only-binary=:all:`;
2. checks the sha256 against the hash in `requirements.txt` and **fails** on mismatch;
3. unpacks the wheel into `python/vendor/`;
4. writes `python/vendor/VENDOR.lock.json` recording package, version, wheel file name,
   hash and the path of the licence file.

Verify an existing tree without touching the network:

```sh
python3 tools/vendor_deps.py --check \
    --requirements examples/pyhello-common/requirements.txt \
    --out examples/pyhello-common/python/vendor
```

Real output from this repository:

```
ok: six 1.17.0 (wheel sha256 4721f391ed90541fddacab5acf947aa0d3dc7d27b2e1e8eda2be8970586c3274)
```

`--clean` empties the output directory first, so a stale package cannot survive an update.
`--cache` points at a download cache directory (git-ignored) so repeated runs do not
re-download.

## 3. Ship them

The build copies `python/vendor/` into the jar next to your modules:

```kotlin
tasks.processResources {
    from("../python") { include("mymod/**"); into("python") }
    from("../python") { include("vendor/**"); into("python") }
}
```

and the metadata names the vendor directory:

* Fabric: `"custom": {"pythonforminecraft": {"vendor": ["python/vendor"]}}`
* NeoForge: `vendor = ["python/vendor"]` under `[modproperties.<modId>]`

At start-up the core unpacks the Python files out of the jar into the game directory and
prepends them to the mod's `sys.path`, ahead of the vendored paths, so a mod always imports
its own modules first. Each mod gets its own paths; two mods may vendor different versions
of the same package without colliding.

## 4. Limits — read before you choose a package

| Limit | Why |
| --- | --- |
| **Pure-Python wheels only** (`py*-none-any`) | A wheel with a compiled extension contains a platform-specific binary. PyFM will not ship or load one: there is no native-image build, no per-OS artifact and no way to verify such a binary here. |
| No transitive dependency resolution | `--no-deps` is used on purpose. Transitive dependencies must be listed explicitly and hash-locked too. That keeps the lock file honest. |
| No `pip` at runtime | By design. If a package needs installation-time code generation, it will not work. |
| No C-extension-backed packages | Anything that ultimately needs `numpy`, `pillow`, `cryptography`, `lxml` and similar will not load. GraalPy supports many of them via its own managed installations, but that requires a GraalPy runtime image and per-platform artifacts, which is outside what this project ships. |
| Licences are not checked | The tool records the licence *file* path but cannot judge a licence. You are responsible for it; see [`../THIRD_PARTY_LICENSES.md`](../THIRD_PARTY_LICENSES.md). |

## 5. Reproducibility checklist

* [ ] `requirements.txt` pins exact versions with hashes
* [ ] `python/vendor/` is committed, not git-ignored
* [ ] `python/vendor/VENDOR.lock.json` is committed
* [ ] `tools/vendor_deps.py --check` passes in CI
* [ ] every vendored package's licence is compatible with your mod's licence

CI runs the `--check` step for the `pyhello_common` example on every push.
