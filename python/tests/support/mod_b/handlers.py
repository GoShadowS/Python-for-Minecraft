"""Handlers of the second test mod: same event and same command name as mod_a."""
import pfm

CALLS = []


def reset():
    CALLS.clear()


@pfm.event("server_start")
def on_server_start(event):
    CALLS.append(("server_start", event.mod_id))


@pfm.command("pyhello")
def pyhello(ctx):
    ctx.reply("hello from mod_b")
