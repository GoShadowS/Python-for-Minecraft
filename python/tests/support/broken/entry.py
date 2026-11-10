import pfm


class Broken:
    def on_initialize(self):
        raise ValueError("intentional failure")
