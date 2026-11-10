"""Handlers of the first test mod, found by pfm.autodiscover()."""
import pfm

CALLS = []


def reset():
    CALLS.clear()


@pfm.event("server_start")
def on_server_start(event):
    CALLS.append(("server_start", event.name, event.mod_id))


@pfm.event("client_tick", side=pfm.Side.CLIENT)
def on_client_tick(event):
    CALLS.append(("client_tick", event.name, event.mod_id))


@pfm.event("server_start", priority=10)
def on_server_start_first(event):
    CALLS.append(("server_start_high", event.name, event.mod_id))


@pfm.command("pyhello", usage="/pyhello", permission=0)
def pyhello(ctx):
    ctx.reply("hello from mod_a")
