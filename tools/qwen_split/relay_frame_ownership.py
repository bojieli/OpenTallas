"""Live relay-chain reservation ownership, independent of stale search candidates."""

class FrameOwnership:
    """A lifted candidate must never erase a later owner's geometry by coordinates."""
    def __init__(self, owners=()):
        self.live = set(owners)

    def release(self, owner, frames, unplace):
        if owner not in self.live:
            return False
        unplace(frames)
        self.live.remove(owner)
        return True

    def mark(self, owner):
        self.live.add(owner)

    def discard(self, owner):
        self.live.discard(owner)
