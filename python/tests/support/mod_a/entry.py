"""Entry point module of the first test mod."""
import pfm

STATE = {"calls": []}


def reset():
    STATE["calls"] = []


class ModA:
    """Class entry point: constructed by pfm, then its hooks are called."""

    def __init__(self):
        STATE["calls"].append("construct")

    def on_initialize(self):
        STATE["calls"].append("initialize")

    def on_client_initialize(self):
        STATE["calls"].append("client_initialize")

    def on_server_initialize(self):
        STATE["calls"].append("server_initialize")


class ModAWithContext:
    """Class entry point that receives the ModContext in its constructor."""

    def __init__(self, ctx):
        STATE["calls"].append("construct:" + ctx.mod_id)

    def on_initialize(self):
        STATE["calls"].append("initialize")


def plain_function():
    """Zero-argument function entry point."""
    STATE["calls"].append("function")


def function_with_context(ctx):
    """One-argument function entry point."""
    STATE["calls"].append("function:" + ctx.mod_id)


def factory():
    """Function entry point that returns an object carrying lifecycle hooks."""
    return ModA()


class Failing:
    def on_initialize(self):
        raise RuntimeError("boom from mod_a")
