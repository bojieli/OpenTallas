#!/usr/bin/env python3
"""Build the case table for the dependent-boundary control probe.

``docs/CHIP_ARCHITECTURE_DESIGN.md`` section 3.6 names five terms of the
exposed dependent chain -- "the last result, mesh transfer, operand readiness,
queue admission, and acknowledged completion" -- and section 13 item 13 says
neither the model's 39 cycles nor the design's historical 120 is measured.
Three of the five are control-path terms with design RTL behind them today,
and ``rtl/test/a3_boundary_control_top.sv`` measures those three on the
modules themselves: ``ot_a3_issue_record_store``, ``ot_a3_event_scoreboard``
and ``ot_a3_mesh_router``.

This tool writes the case table those checkers read.  It predicts **no cycle
count**: the cycles are the measurement.  What it predicts is the protocol
outcome of each case -- whether the wait passes and, if not, with which trap
class -- from the rule section 3.6 states, so a run whose timing looked
plausible but whose scoreboard did the wrong thing is a FAIL rather than a
number.

The rule, transcribed from section 3.6 and checked against
``runtime.abi3.constants`` for the trap class:

    a wait set passes when every producer is `signalled` (and `published`
    under WAIT_ACQUIRE / ACQUIRE ordering); it stalls while any producer is
    `pending`; it traps 13 if a producer is neither.

Layout of one case (16 words; transcribed identically in
``rtl/test/a3_boundary_control_top.sv``, ``rtl/test/tb_a3_boundary_control.sv``
and ``rtl/test/a3_boundary_control_harness.cpp``)::

     0 producer_count      6 pending_delay      12 unsignalled_producer
     1 ordering byte       7 queue index        13 tag
     2 acquire flag        8 preload            14 admit_release_delay
     3 release flag        9 dest_x (hops)      15 reserved
     4 first event id     10 expect_trap_class
     5 leave_one_pending  11 expect_wait_ok
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.abi3.constants import Ordering, TrapClass  # noqa: E402

SCHEMA = "opentallas.rtl.abi3_boundary_control_vectors.v1"
CASE_STRIDE = 16
META_WORDS = 8
MAX_PRODUCERS = 12          # runtime.abi3.descriptors.MAX_WAIT_PRODUCERS
IRS_QUEUE_DEPTH = 16        # rtl/abi3/ot_a3_pkg.sv A3_QUEUE_DEPTH
MESH_X = 4                  # rtl/test/a3_boundary_control_top.sv MESH_X


@dataclass
class BoundaryCase:
    name: str
    note: str
    producers: int
    ordering: int = 0
    acquire: int = 0
    release: int = 0
    first_event: int = 0
    leave_one_pending: int = 0
    pending_delay: int = 0
    queue: int = 0
    preload: int = 0
    dest_x: int = 1
    unsignalled: int = 0
    admit_release: int = 0
    tag: int = 0
    # filled by the rule below
    expect_trap_class: int = 0
    expect_wait_ok: int = 1
    expect_stalled: int = 0
    words: list[int] = field(default_factory=list)


def outcome(case: BoundaryCase) -> None:
    """Section 3.6's wait rule, applied to the state this case builds.

    Not a reading of the RTL: the three states a producer can be in are the
    ABI's, and the case table decides which one each producer is left in.
    """
    if case.unsignalled:
        # never issued to the scoreboard and never completed: neither pending
        # nor signalled
        case.expect_trap_class = int(TrapClass.INTERNAL_INVARIANT)
        case.expect_wait_ok = 0
        case.expect_stalled = 0
        return
    case.expect_trap_class = int(TrapClass.NONE)
    case.expect_wait_ok = 1
    # one producer left outstanding is `pending`: the wait must stall and then
    # pass, which is exactly the case section 3.6 says is NOT a trap
    case.expect_stalled = 1 if case.leave_one_pending else 0


def build_cases() -> list[BoundaryCase]:
    cases: list[BoundaryCase] = []

    def add(**kw: Any) -> None:
        case = BoundaryCase(**kw)
        case.tag = len(cases) + 1
        outcome(case)
        cases.append(case)

    # -- the boundary at every wait-set width the ABI allows ---------------
    # Twelve producers are looked up four at a time over three chunks, so a
    # wider wait set must NOT cost more; this sweep is what says so.
    for n, ev in ((1, 100), (2, 120), (3, 140), (4, 200), (6, 220),
                  (8, 250), (10, 270), (MAX_PRODUCERS, 300)):
        add(name=f"width_{n}", producers=n, first_event=ev,
            note=f"{n} producers, one mesh hop, empty queue")

    # -- the boundary at every mesh distance the probe's fabric spans ------
    for hops in range(MESH_X):
        add(name=f"hops_{hops}", producers=MAX_PRODUCERS, first_event=400 + 20 * hops,
            dest_x=hops,
            note=f"{hops} hop(s) between the producer's node and the consumer's")

    # -- the orderings that make `published` a precondition ----------------
    for label, order in (("acquire", Ordering.ACQUIRE),
                         ("acquire_release", Ordering.ACQUIRE_RELEASE),
                         ("sequential", Ordering.SEQUENTIAL)):
        add(name=f"order_{label}", producers=4, ordering=int(order), acquire=1,
            release=1, first_event=500 + 20 * int(order),
            note=f"{label} ordering: the producer must be published, not only signalled")

    # -- a producer still outstanding: the wait stalls and then passes -----
    for delay in (8, 20, 64):
        add(name=f"stall_{delay}", producers=4, first_event=600 + delay,
            leave_one_pending=1, pending_delay=delay,
            note=f"one producer completes {delay} cycles into the wait")

    # -- a producer that is neither pending nor signalled: trap 13 ---------
    for n in (1, 4, MAX_PRODUCERS):
        add(name=f"unsignalled_{n}", producers=n, first_event=700 + 20 * n,
            unsignalled=1,
            note="no producer was ever issued or completed: section 3.6's trap 13")

    # -- admission under occupancy and behind a full queue -----------------
    add(name="occupancy_12", producers=4, first_event=800, preload=12,
        note="twelve operations already in the store when the consumer arrives")
    for release in (12, 40):
        add(name=f"queue_full_{release}", producers=4, first_event=900 + release,
            queue=3, preload=IRS_QUEUE_DEPTH, admit_release=release,
            note=f"the consumer's queue is full and drains {release} cycles later")
    return cases


def emit(cases: list[BoundaryCase], out_dir: Path) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    words: list[int] = []
    for case in cases:
        rec = [
            case.producers, case.ordering, case.acquire, case.release,
            case.first_event, case.leave_one_pending, case.pending_delay,
            case.queue, case.preload, case.dest_x, case.expect_trap_class,
            case.expect_wait_ok, case.unsignalled, case.tag,
            case.admit_release, 0,
        ]
        assert len(rec) == CASE_STRIDE
        case.words = rec
        words.extend(rec)
    meta = [len(cases), 0, 0, 0, 0, 0, 0, 0]
    (out_dir / "bc_case.hex").write_text(
        "".join(f"{w:08x}\n" for w in words), encoding="utf-8")
    (out_dir / "bc_meta.hex").write_text(
        "".join(f"{w:08x}\n" for w in meta), encoding="utf-8")
    digests = {
        name: hashlib.sha256((out_dir / name).read_bytes()).hexdigest()
        for name in ("bc_case.hex", "bc_meta.hex")
    }
    return {
        "schema": SCHEMA,
        "case_count": len(cases),
        "case_stride": CASE_STRIDE,
        "mesh_x": MESH_X,
        "max_producers": MAX_PRODUCERS,
        "queue_depth": IRS_QUEUE_DEPTH,
        "image_sha256": digests,
        "wait_rule": (
            "a wait set passes when every producer is signalled (and published "
            "under WAIT_ACQUIRE / ACQUIRE ordering); it stalls while any "
            "producer is pending; it traps "
            f"{int(TrapClass.INTERNAL_INVARIANT)} if a producer is neither "
            "(docs/CHIP_ARCHITECTURE_DESIGN.md section 3.6)"
        ),
        "predicts": (
            "the protocol outcome of every case -- wait_ok and trap class -- "
            "and nothing about cycles: the cycles are the measurement"
        ),
        "cases": [
            {
                "index": i, "name": c.name, "note": c.note, "tag": c.tag,
                "producers": c.producers, "ordering": c.ordering,
                "acquire": c.acquire, "release": c.release,
                "first_event": c.first_event,
                "leave_one_pending": c.leave_one_pending,
                "pending_delay": c.pending_delay, "queue": c.queue,
                "preload": c.preload, "dest_x": c.dest_x,
                "unsignalled": c.unsignalled, "admit_release": c.admit_release,
                "expect_trap_class": c.expect_trap_class,
                "expect_wait_ok": c.expect_wait_ok,
                "expect_stalled": c.expect_stalled,
            }
            for i, c in enumerate(cases)
        ],
    }


def build(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, default=None)
    args = parser.parse_args(argv)
    cases = build_cases()
    manifest = emit(cases, args.out_dir)
    if args.manifest:
        args.manifest.parent.mkdir(parents=True, exist_ok=True)
        args.manifest.write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"boundary control: {len(cases)} cases -> {args.out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(build())
