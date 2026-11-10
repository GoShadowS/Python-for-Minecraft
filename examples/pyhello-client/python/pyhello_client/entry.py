"""Entry point and handlers of the client-only smoke test.

Every line this mod writes starts with ``[pyhello-client]`` so the smoke test in
``docs/testing.md`` can be checked with a single grep of the log.
"""
import pfm

from . import MARKER

TICKS_LOGGED = 0


class PyHelloClient:
    """Client entry point. Python-for-Minecraft constructs it and calls the hook."""

    def on_client_initialize(self):
        pfm.log.info("%s client entry point ran on the %s side" % (MARKER, pfm.side()))
        pfm.log.info("%s java interop: %s" % (MARKER, _java_probe()))


def _java_probe():
    """Proves Java interop: resolve a Java class through the bridge."""
    try:
        cls = pfm.java.import_class("net.minecraft.client.Minecraft")
        return "resolved %s" % cls
    except Exception as exc:  # noqa: BLE001 - reported, never fatal
        return "unavailable (%s)" % exc


@pfm.event("client_start")
def on_client_start(event):
    pfm.log.info("%s client_start, client handle present: %s"
                 % (MARKER, pfm.mc.client is not None))


@pfm.event("client_tick")
def on_client_tick(event):
    global TICKS_LOGGED
    TICKS_LOGGED += 1
    if TICKS_LOGGED in (1, 100):
        pfm.log.info("%s client_tick #%d" % (MARKER, TICKS_LOGGED))


@pfm.command("pyhello", usage="/pyhello")
def pyhello(ctx):
    ctx.reply("%s hello from client-side Python" % MARKER)
