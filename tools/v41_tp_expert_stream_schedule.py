#!/usr/bin/env python3
"""Bound a data-ready V4.1 MoE w2 schedule without changing its arithmetic.

This is a scheduling sensitivity, not an RTL timing result.  The existing
64-byte, four-rank activation gather is measured as one blocking descriptor.
The proposed protocol keeps one descriptor but lays its output out in expert
order.  A ready bit for each complete expert activation lets the QE execute
that expert's output rows while later expert activations arrive.  Expert
results are still BF16-rounded and accumulated in expert-ID order.

The optimistic mode assumes this overlap is possible despite COLL-v1's
blocking instruction issue; it therefore states the required ISA/VM changes
explicitly and must not be used as an adopted throughput claim.
"""

from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import arch_lanes_v41 as AL  # noqa: E402
import collective_exposure as CX  # noqa: E402
import decode_critical_path as DC  # noqa: E402
from v41_tp_exact_reprice import v41_moe_rowsplit  # noqa: E402
from v41_tp_rowsplit_measured_reprice import measured_gather_mutation  # noqa: E402

BENCH = ROOT / "results/rtl/v41_tp_rowsplit_die_collectives.json"
PRICED = ROOT / "results/arch/v41_tp_rowsplit_measured_reprice.json"
OUT = ROOT / "results/arch/v41_tp_expert_stream_schedule.json"


def schedule(gather_tail: int, down_cycles: int, *, experts: int = 7,
             local_words: int = 38, ranks: int = 4, group_size: int = 1) -> dict:
    """Integer-cycle, single-QE schedule at a one-VM-write/cycle output floor.

    The aggregate tail starts at the last local activation word.  It is a
    *measured* tail, including transport/startup/queueing.  Assigning its
    final ranks*local_words*experts cycles to expert-major output gives the
    earliest complete-expert readiness permitted by the one-port VM.  This
    is an optimistic bound; the present RTL does not export these ready bits.
    """
    total_words = experts * local_words * ranks
    assert gather_tail >= total_words
    assert 1 <= group_size <= experts
    work = [down_cycles // experts + (e < down_cycles % experts)
            for e in range(experts)]
    ready = [gather_tail - total_words + min(experts, (e // group_size + 1) * group_size) * local_words * ranks
             for e in range(experts)]
    finish = []
    for e in range(experts):
        finish.append(max(ready[e], finish[-1] if finish else 0) + work[e])
    serial = gather_tail + down_cycles
    assert finish[-1] <= serial
    return dict(group_size=group_size, expert_ready_cycles=ready, expert_w2_cycles=work,
                expert_finish_cycles=finish, serial_completion_cycles=serial,
                scheduled_completion_cycles=finish[-1], hidden_w2_cycles=serial - finish[-1],
                vm_output_words=total_words, vm_minimum_cycles=total_words,
                arithmetic_order=list(range(experts)))


def _stream_mutation(remaining_down_fraction: float):
    def apply(g, _spec):
        for name, n in g.nodes.items():
            if name.endswith(".ffn.down"):
                # Aggregate w2 throughput is unchanged.  Only the portion
                # exposed after the last complete activation arrives remains
                # on the critical path.  Earlier work is scheduled in the
                # gather's measured one-word/cycle receive window.
                n["issue"] *= remaining_down_fraction
                n["depth"] *= remaining_down_fraction
                n["_expert_stream_optimistic"] = True
    return apply


def build() -> dict:
    bench = json.loads(BENCH.read_text())
    priced = json.loads(PRICED.read_text())
    assert bench["schema"] == "v41_tp_rowsplit_die_collectives_v1"
    for path, digest in bench["source_sha256"].items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == digest, path
    tails = {p: bench["summary"][p]["measured_tail_cycles"] for p in ("act", "y")}
    assert tails == priced["measured_tail_cycles"]
    point = AL.design_point()
    lane = json.loads((ROOT / "results/arch/v41_lanes.json").read_text())
    lev = lane["collective_exposure"]["levers"]
    muts = point["muts"] + [point["ml"], CX.mutation(lev["terms"]),
                            CX.consumer_mutation(tuple(lev["consumers"])),
                            measured_gather_mutation(tails)]
    old = DC.v41_moe
    DC.v41_moe = v41_moe_rowsplit
    try:
        # Extract the full w2 critical-path interval in cycles from the same
        # current-source DAG used by the transfer-pricing tool.
        with AL.LX.clock(point["hz"][0]), AL.U.params(**point["hz"][1]):
            solved = AL.U.solve(point["sp"], 1_048_576, levers=AL.U.CHAIN_L3,
                                muts=muts)
        down = solved["_built"].g.nodes["L0.ffn.down"]
        hz = AL.A._env()["clock"]
        down_cycles = math.ceil((down["issue"] + down["depth"]) * hz)
        schedules = {str(group): schedule(tails["act"], down_cycles, group_size=group)
                     for group in (1, 2, 3, 7)}
        points = {}
        for ctx in (1_048_576, 200_000):
            base = AL.LX.evaluate(point["sp"], ctx, muts, hz=point["hz"],
                                  draft_extra_s=point["draft_extra_s"])
            pinned = priced["points"][str(ctx)]["ar"]["row_split_measured_gathers"]
            assert abs(base["ar"] - pinned) < 1e-7, (ctx, base["ar"], pinned)
            variants = {}
            for group, sch in schedules.items():
                fraction = (down_cycles - sch["hidden_w2_cycles"]) / down_cycles
                piped = AL.LX.evaluate(point["sp"], ctx,
                                       muts + [_stream_mutation(fraction)],
                                       hz=point["hz"], draft_extra_s=point["draft_extra_s"])
                variants[group] = dict(ar_optimistic_schedule=piped["ar"],
                                       gain_fraction=piped["ar"] / base["ar"] - 1)
            points[str(ctx)] = dict(ar_baseline=base["ar"], by_ready_group=variants)
    finally:
        DC.v41_moe = old
    srcs = ("tools/v41_tp_expert_stream_schedule.py", "tools/v41_tp_rowsplit_measured_reprice.py",
            "tools/v41_tp_exact_reprice.py", "tools/arch_lanes_v41.py",
            "tools/decode_critical_path.py", "tools/collective_exposure.py",
            "results/arch/v41_lanes.json", "results/arch/v41_tp_rowsplit_measured_reprice.json",
            "results/rtl/v41_tp_rowsplit_die_collectives.json")
    return dict(schema="v41_tp_expert_stream_schedule_v1",
                source_sha256={p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in srcs},
                scope="optimistic data-ready schedule sensitivity over measured blocked 16-entry RTL gather tails; not executed RTL or chip throughput",
                contract=dict(experts=7, ranks=4, local_activation_flits_per_expert=38,
                              flit_bytes=64, vm_result_writes_per_cycle=1,
                              one_collective_descriptor=True,
                              per_expert_bf16_rounding=True,
                              expert_sum_order="ascending expert ID, shared last"),
                schedules=schedules, points=points,
                requirements=["one activation gather descriptor that emits expert-major flits across ranks",
                              "per-expert complete-data ready bits before w2 reads that expert",
                              "nonblocking or yieldable COLL issue so QE can run while DMA owns VM port B",
                              "VM port arbitration or bank separation: QE read and DMA writes must coexist without conflict",
                              "no change to per-expert FP32 accumulation, BF16 rounding, or ascending-ID expert sum"],
                limits=["the current COLL-v1 core blocks issue until the whole gather completes",
                        "current engine output ordering and per-expert readiness are not RTL verified",
                        "the measured 16-entry gather stalls its producer heavily; work overlap may not attain the optimistic bound",
                        "MTP payload and schedule are different and are not repriced",
                        "model retains other inherited collective and index terms; no full-shape bit-exact or die P&R claim"])


if __name__ == "__main__":
    rec = build()
    OUT.write_text(json.dumps(rec, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"hidden_w2_cycles": {g: s["hidden_w2_cycles"] for g, s in rec["schedules"].items()},
                      "points": rec["points"]}, indent=2))
