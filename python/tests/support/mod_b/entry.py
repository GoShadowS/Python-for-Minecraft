"""Entry point module of the second test mod (isolation checks)."""
import pfm

SECRET = "mod_b"
STATE = {"calls": []}


def reset():
    STATE["calls"] = []


class ModB:
    def on_initialize(self):
        STATE["calls"].append("initialize")
        self.mod = pfm.mod_id()
