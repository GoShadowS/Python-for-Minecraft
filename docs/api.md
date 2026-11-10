# Public API, entrypoints and events

This is the whole public surface of the `pfm` package (`python/pfm`, version `1.0.0`). It is
the only API a Python mod may use. Everything else in `python/pfm` is private (leading
underscore) and may change.

The Python side is covered by 92 unit tests in `python/tests`. The Java side that calls it
has **never been compiled**; see [`testing.md`](testing.md).

## 1. Entry points

Declared in the mod metadata as `package.module:Attribute`. The attribute may be:

| Attribute kind | What PyFM does |
| --- | --- |
| a class | instantiates it once with no arguments, keeps the instance for the whole life of the mod |
| an object (any instance) | uses it as-is |
| a callable (function, classmethod, lambda) | calls it once with no arguments |

The same attribute is used for every phase, so state stored on `self` survives from
`on_initialize` to `on_client_initialize`. (This was a real bug the test suite caught: an
earlier implementation created a new entrypoint object per phase and silently lost that
state.)

### Lifecycle hooks

| Hook | Runs when | Side |
| --- | --- | --- |
| `on_initialize(self)` | after the mod's runtime is created | both |
| `on_client_initialize(self)` | client start-up | client only |
| `on_server_initialize(self)` | server start-up | dedicated server (and integrated server if the adapter fires it) |

Missing hooks are not an error. `pfm.PHASES == ('initialize', 'client_initialize',
'server_initialize')` and `pfm.LIFECYCLE` maps each phase to its hook name.

## 2. Events

```python
import pfm

@pfm.event("server_start")
def on_server_start(event):
    pfm.log.info("server is up, handle present: %s" % (pfm.mc.server is not None))
```

`pfm.event(name)` and its alias `pfm.on(name)` are decorators. They may only be used while
Python-for-Minecraft is initialising a mod; using them at any other time raises
`pfm.HandlerError` rather than silently registering a handler that never runs.

Nine event names exist. They are the same on Fabric and NeoForge:

| Name | Fired | Payload (`event.data`) |
| --- | --- | --- |
| `initialize` | after the common entry point ran | `None` |
| `client_start` | client finished starting | `None` |
| `client_stop` | client is stopping | `None` |
| `server_start` | dedicated or integrated server is starting | `None` |
| `server_stop` | server is stopping | `None` |
| `client_tick` | one client tick, on the client thread | `None` |
| `server_tick` | one server tick, on the server thread | `None` |
| `player_join` | a player joined | the player handle |
| `player_leave` | a player left | the player handle |

A handler that raises does not stop other handlers or other mods. `pfm.dispatch(name, data)`
returns a `pfm.DispatchReport` listing per-mod results, and `pfm.fire(name, data)` is the
mod-facing way to emit a custom event to the same mod only.

Handlers run on the thread that fired the event — the client thread for `client_*`, the
server thread for `server_*`. PyFM does not move work between threads; a handler that needs
to defer work must do it itself.

## 3. Commands

```python
@pfm.command("pyhello", usage="/pyhello", permission=0)
def pyhello(ctx):
    ctx.reply("hello from Python")
    pfm.log.info("args=%s" % (ctx.args,))
```

`ctx` is a `pfm.CommandContext` with `.source`, `.args` (list of strings) and `.reply(text)`.
Registration goes through the bridge to the loader, which builds the real command node
(Brigadier on Fabric and NeoForge). `ctx.reply` on a source that cannot receive messages is
silently ignored. The name must be a single word with no leading slash; `pfm.CommandSpec`
rejects anything else at registration time, not at execution time.

## 4. Java interop

```python
cls = pfm.java.import_class("net.minecraft.server.MinecraftServer")
```

`pfm.java.import_class(fqcn)` resolves a Java class through the bridge and returns whatever
the runtime hands back. This is the **only** supported interop path.

What this does and does not give you:

* it gives you the class, so you can call static members and use returned instances;
* it does **not** wrap any Minecraft API. There is no `pfm.block`, no `pfm.registry`, no
  `pfm.screen`. Anything beyond the handles in §5 is raw interop, untested and unsupported;
* it is not a substitute for mixins, access wideners or core mods. PyFM cannot transform
  Minecraft classes.

## 5. Handles

`pfm.mc` exposes exactly three handles, and only the ones valid on the current side:

| Handle | Available on | Contains |
| --- | --- | --- |
| `pfm.mc.server` | server side | the server object |
| `pfm.mc.client` | client side | the client object |
| `pfm.mc.player` | client side | the local player |

On a dedicated server, `pfm.mc.client` and `pfm.mc.player` are `None`. Asking for a handle
that does not exist on this side returns `None`; it does not raise.

## 6. Logging

`pfm.log` is a ready-made logger; `pfm.get_logger("my area")` makes a named one. Output goes
through the bridge into the game log, prefixed `[PyFM]`. Levels: `debug`, `info`, `warn`,
`error`.

## 7. Runtime and introspection

| Call | Result |
| --- | --- |
| `pfm.mod_id()` | this mod's id |
| `pfm.side()` | `pfm.Side.CLIENT` or `pfm.Side.SERVER` |
| `pfm.is_client()` / `pfm.is_server()` | booleans |
| `pfm.context()` | the `ModContext` for this mod (mod id, side, metadata) |
| `pfm.runtime()` | this mod's `ModRuntime` |
| `pfm.runtime_for(mod_id)` | another mod's runtime, if loaded |
| `pfm.all_runtimes()` | every loaded runtime |
| `pfm.autodiscover("pkg.handlers")` | import every module in a package and register what they declare |

`pfm.side()` and `pfm.mod_id()` raise `pfm.HandlerError` outside a mod runtime — that is
deliberate, so a mod cannot accidentally read another mod's context.

## 8. Errors

| Exception | Raised when |
| --- | --- |
| `pfm.PyFmError` | base class |
| `pfm.EntrypointError` | the entry point could not be resolved or a lifecycle hook failed |
| `pfm.HandlerError` | an event handler failed, or the API was used outside a runtime |
| `pfm.BridgeError` | the Java bridge reported a failure |

`pfm.format_exception(exc)` renders the guest traceback with the mod id, the phase and
`at file:line` frames. A failing mod is recorded as failed; the other mods still load. No
failed mod is reported as loaded.

## 9. What is deliberately absent

* No registry API, no block/item/screen API, no datapack API.
* No sandbox, no permission model. See [`security.md`](security.md).
* No async/await integration with the game loop.
* No hot reload.
* No compile step, so no type checking for mods.
