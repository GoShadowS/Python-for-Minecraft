"""Entry point and handlers of the common/server smoke test.

The same module runs on the client and on a dedicated server; which hooks execute depends
on the side Python-for-Minecraft started the runtime on. It also imports ``six``, which is
vendored into this mod jar by ``tools/vendor_deps.py``.
"""
import pfm
import six

from . import MARKER

JOINS = 0


class PyHelloCommon:
    """Common entry point; both lifecycle hooks are side-specific."""

    def on_initialize(self):
        pfm.log.info("%s common entry point ran on the %s side" % (MARKER, pfm.side()))
        pfm.log.info("%s vendored dependency six %s is importable"
                     % (MARKER, six.__version__))

    def on_server_initialize(self):
        pfm.log.info("%s dedicated-server entry point ran" % MARKER)


@pfm.event("server_start")
def on_server_start(event):
    pfm.log.info("%s server_start, server handle present: %s"
                 % (MARKER, pfm.mc.server is not None))


@pfm.event("server_tick")
def on_server_tick(event):
    # Deliberately cheap: ticking handlers must not do work every tick.
    return None


@pfm.event("server_stop")
def on_server_stop(event):
    pfm.log.info("%s server_stop" % MARKER)


@pfm.event("player_join")
def on_player_join(event):
    global JOINS
    JOINS += 1
    pfm.log.info("%s player_join #%d: %s" % (MARKER, JOINS, event.data))


@pfm.command("pyhello", usage="/pyhello", permission=0)
def pyhello(ctx):
    ctx.reply("%s hello from Python on the %s side (six %s)"
              % (MARKER, pfm.side(), six.__version__))
