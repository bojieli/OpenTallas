"""Seeded asynchronous completion for the golden device (section 3.2 items 2-3).

``runtime.sim.device.Device`` executes every engine instruction synchronously at
issue: the memory bytes, the tokens and every value-producing step are
produced there and are unchanged by anything in this module.  What the
asynchronous front end of docs/CHIP_ARCHITECTURE_DESIGN.md changes is the
*accounting* of retirement -- an engine instruction leaves the front end at
issue with a serial and completes later, in an order the engines choose, at
most 16 per queue and 32 per die outstanding -- and the event scoreboard's
``pending`` state that exists between the two.  A :class:`RunAheadPolicy`
makes the golden model defer exactly that accounting, with a seeded delay and
order, so the device is the oracle for the RTL under the same run-ahead the
RTL's checkers apply, and so that a difference between a policy and no policy
in anything but timing would be a defect of the model.

What a policy may change: when ``instructions.retired`` advances, when a
signal event becomes signalled/published, the ``queue.max_occupancy`` counter
(group 0x02, written only under a policy), and which wait sets *stall* (a
pending producer) rather than trap.  What it may not change: any issued
operation, resolved view, predicate outcome, written byte, ``retired``,
``fetched``, ``predicated_off``, the trap class, ``first_fault_instruction``
or any counter outside ``queue.max_occupancy``; ``tests/runtime/
test_abi3_run_ahead.py`` holds that invariance over every constructed
program of the microsequencer campaign.

The queue mapping is the RTL's (``rtl/abi3/ot_a3_pkg.sv a3_queue_base``):
family base plus SCHEDULE.queue_index for an OPERATOR that names a SCHEDULE
(index 0 without one), COMMUNICATION.virtual_channel for LINK, and the state
queue for STATE, OBSERVATION and RECOVERY.  The PRNG is xorshift32, the same
generator the RTL checkers use, so a seed names one completion schedule.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from runtime.abi3.constants import Major

#: The front end's bounds (docs/CHIP_ARCHITECTURE_DESIGN.md section 2.1 rows
#: 14-15, [T2.1-14], [T2.1-15]); the RTL holds the same values in
#: ``rtl/abi3/ot_a3_pkg.sv``.
MAX_OUTSTANDING = 32
QUEUE_DEPTH = 16
QUEUE_COUNT = 23
STATE_QUEUE = 22

_QUEUE_BASE = {
    int(Major.TENSOR): 0,
    int(Major.VECTOR): 4,
    int(Major.ATTENTION): 8,
    int(Major.REDUCTION): 10,
    int(Major.ROUTE): 12,
    int(Major.SELECTION): 13,
    int(Major.DMA): 14,
    int(Major.LINK): 18,
}
_QUEUE_MASK = {
    int(Major.TENSOR): 3,
    int(Major.VECTOR): 3,
    int(Major.DMA): 3,
    int(Major.LINK): 3,
    int(Major.ATTENTION): 1,
    int(Major.REDUCTION): 1,
}


def queue_for(major: int, index: int) -> int:
    """The issue queue of an instruction: family base plus the folded index."""
    base = _QUEUE_BASE.get(int(major))
    if base is None:
        return STATE_QUEUE
    return base + (int(index) & _QUEUE_MASK.get(int(major), 0))


def xorshift32(state: int) -> int:
    state &= 0xFFFFFFFF
    state ^= (state << 13) & 0xFFFFFFFF
    state ^= state >> 17
    state ^= (state << 5) & 0xFFFFFFFF
    return state & 0xFFFFFFFF


@dataclass(frozen=True)
class RunAheadPolicy:
    """How far, and in what order, the golden model lets completion lag issue.

    ``max_delay`` is in issue serials: an operation issued with serial ``s``
    becomes due at ``s + 1 + rand % max_delay`` (``max_delay`` 0: due at once,
    which is the sequential model's own accounting).  With ``reorder`` the
    completion drawn among the due ones is chosen by ``rand % count`` rather
    than oldest first.
    """

    seed: int
    max_delay: int
    max_outstanding: int = MAX_OUTSTANDING
    per_queue: int = QUEUE_DEPTH
    reorder: bool = True

    def __post_init__(self) -> None:
        if self.max_delay < 0:
            raise ValueError("max_delay must be non-negative")
        if not 1 <= self.max_outstanding <= MAX_OUTSTANDING:
            raise ValueError(f"max_outstanding must be 1..{MAX_OUTSTANDING}")
        if not 1 <= self.per_queue <= QUEUE_DEPTH:
            raise ValueError(f"per_queue must be 1..{QUEUE_DEPTH}")


@dataclass
class Outstanding:
    serial: int
    pc: int
    event_id: int
    flags: int
    queue: int
    due: int


@dataclass
class RunAheadState:
    """The outstanding set of one transaction under a policy."""

    policy: RunAheadPolicy
    rng: int = 0
    entries: list[Outstanding] = field(default_factory=list)
    queue_counts: dict[int, int] = field(default_factory=dict)
    max_occupancy: int = 0

    def __post_init__(self) -> None:
        self.rng = (self.policy.seed | 1) & 0xFFFFFFFF

    def draw(self) -> int:
        self.rng = xorshift32(self.rng)
        return self.rng

    # -- the set -----------------------------------------------------------
    def pending(self, event_id: int) -> bool:
        return any(entry.event_id == event_id for entry in self.entries)

    def queue_full(self, queue: int) -> bool:
        return self.queue_counts.get(queue, 0) >= self.policy.per_queue

    def full(self) -> bool:
        return len(self.entries) >= self.policy.max_outstanding

    def push(self, serial: int, pc: int, event_id: int, flags: int, queue: int) -> Outstanding:
        delay = 0 if self.policy.max_delay == 0 else 1 + (self.draw() % self.policy.max_delay)
        entry = Outstanding(serial, pc, event_id, flags, queue, serial + delay)
        self.entries.append(entry)
        self.queue_counts[queue] = self.queue_counts.get(queue, 0) + 1
        self.max_occupancy = max(self.max_occupancy, len(self.entries))
        return entry

    def pop_due(self, serial: int) -> Outstanding | None:
        """One due operation to complete now, or None."""
        due = [entry for entry in self.entries if entry.due <= serial]
        if not due:
            return None
        chosen = due[self.draw() % len(due)] if self.policy.reorder else due[0]
        return self._remove(chosen)

    def pop_any(self) -> Outstanding | None:
        """One outstanding operation to complete now, due or not."""
        if not self.entries:
            return None
        chosen = (
            self.entries[self.draw() % len(self.entries)]
            if self.policy.reorder
            else self.entries[0]
        )
        return self._remove(chosen)

    def _remove(self, entry: Outstanding) -> Outstanding:
        self.entries.remove(entry)
        self.queue_counts[entry.queue] -= 1
        return entry
