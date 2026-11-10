# Trust, security and permissions

**Python-for-Minecraft is not a sandbox.** This page exists so that nobody has to guess what
that means. Do not load Python code you do not trust.

## 1. What Python mod code can do

The Python runtime is GraalPy running **inside the game's own JVM process**, with host access
enabled by default (`python.allowAllAccess=true`). Concretely, Python mod code can:

* read and write any file the game process can reach — including the user's home directory,
  `.ssh`, browser profiles, other Minecraft instances;
* open network connections, download and upload anything;
* call arbitrary Java through `pfm.java.import_class`, including `java.lang.Runtime`, so it
  can start subprocesses;
* read and modify the state of other mods, of the JVM and of the game itself;
* exhaust memory or CPU and take the whole process down.

This is the same trust level as a Java mod. Neither Kotlin for Forge nor Fabric Language
Kotlin sandboxes mod code either; PyFM simply does not pretend to be different.

## 2. What PyFM does *not* give a Python mod

These are real limits, and they are the difference between "trusted" and "unbounded":

* **No class transformation.** PyFM has no mixin support, no access wideners, no bytecode
  rewriting. A Python mod cannot patch Minecraft or another mod.
* **No loader-level privileges.** A Python mod is discovered and loaded by PyFM, not by the
  loader. It cannot register its own language adapter, change mod metadata, or influence
  mod load order.
* **No cross-mod imports.** Each Python mod has its own GraalPy `Context` and its own
  `sys.path`. One mod cannot `import` another mod's modules, and a failure in one mod does
  not take the others down. Isolation of *namespaces* is implemented and tested; isolation
  of *authority* is not, because all contexts run in the same JVM with the same host access.
* **No new threads that touch the game.** Handlers run on the thread that fired the event.
  PyFM does not schedule Python work onto other threads. (Python code can of course start
  its own threads; nothing prevents that.)

## 3. The one knob

`<game directory>/config/pythonforminecraft.properties`:

| Key | Default | Effect |
| --- | --- | --- |
| `python.allowAllAccess` | `true` | Host access handed to the GraalPy context. `false` builds the context with `allowAllAccess(false)`. |
| `python.workDir` | `pythonforminecraft` | Directory, relative to the game directory, where Python sources are unpacked. |
| `python.debug` | `false` | Per-event dispatch summaries at info level. |

**Warning about `python.allowAllAccess=false`:** the flag is implemented and is passed to the
Truffle context builder, but it has **never been exercised** — no JVM was available to run
it. With host access restricted, `pfm.java.import_class` and most handles will stop working,
so a mod that uses interop will fail. Treat this setting as untested: it is a starting point
for anyone who wants to build a real restricted mode, not a supported security boundary.

## 4. Server operators

If you run a dedicated server:

* treat the `mods/` directory as an executable allowlist. A Python mod jar is code with the
  same reach as the server process.
* the server-capable component is a separate jar (`pythonforminecraft_server`) precisely so
  that a server never has to install the client component. That reduces surface, not
  privilege.
* there is no per-mod permission system. If you need to know what a mod does, read its
  Python source — it is plain text inside the jar, under `python/`.

## 5. What would have to change for a real sandbox

Recorded here so the gap is explicit rather than implied:

1. A threat model. "Untrusted mod" on a client and on a public server are different problems.
2. GraalVM `SandboxPolicy` (or equivalent) with a resource limit, a CPU-time limit and no
   host access — and a decision about whether Python mods keep any interop at all.
3. A capability API replacing `pfm.java.import_class`: a curated allowlist of game objects,
   since unrestricted interop and a sandbox are mutually exclusive.
4. Verification. A sandbox that has not been attacked is not a sandbox.

None of that exists today. Until it does, the honest statement is: **Python mods are trusted
code.**

## 6. Supply chain

* Python dependencies are vendored at build time and hash-locked
  ([`dependencies.md`](dependencies.md)), so a game never fetches code at start-up. The
  hashes protect against a changed wheel, not against a malicious package you chose to
  vendor.
* `tools/vendor_deps.py` records each package's licence file but does not evaluate licences.
* Python mod jars are distributed by their own authors through whatever channel they choose.
  PyFM signs nothing and verifies no signature.
