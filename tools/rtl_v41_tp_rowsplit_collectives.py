#!/usr/bin/env python3
"""Measure the two bit-exact TP row-split gathers on the existing one-shot RTL.

This is a producer-stub stage bench, not full-shape core execution. Its
producer issue/depth and ideal-overlap exposure come from the current V4.1
design-point DAG. It drives the validated T1 behavioural link and the actual
one-shot gather engine at the die's CL_LANES=16: 266 activation and 80 output
64-byte flits per die.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import arch_lanes_v41 as AL  # noqa: E402
import decode_critical_path as DC  # noqa: E402
import rtl_v41_stage_collective_campaign as C  # noqa: E402
from v41_tp_exact_reprice import v41_moe_rowsplit  # noqa: E402

OUT = ROOT / "results/rtl/v41_tp_rowsplit_collectives.json"
C.LANES = 16  # ot_chip_v41x_die.CL_LANES; one 512-bit VM word per collective flit
C.WORD_B = 4 * C.LANES


def patterns_from_design_point() -> dict:
    old = DC.v41_moe
    DC.v41_moe = v41_moe_rowsplit
    try:
        point = AL.design_point()
        with AL.LX.clock(point["hz"][0]), AL.U.params(**point["hz"][1]):
            solution = AL.U.solve(point["sp"], 1_048_576, levers=AL.U.CHAIN_L3,
                                  muts=point["muts"] + [point["ml"]])
    finally:
        DC.v41_moe = old
    g = solution["_built"].g
    specs = (("act", "L0.ffn.quant2", "L0.ffn.act_allgather", 266),
             ("y", "L0.ffn.down", "L0.ffn.y_allgather", 80))
    out = {}
    for label, producer, collective, words in specs:
        p, c = g.nodes[producer], g.nodes[collective]
        assert c["op"] == "all_gather" and c["payload"] == words * C.WORD_B * 4
        issue = math.ceil(p["issue"] * C.CLOCK - 1e-9)
        depth = math.ceil(p["depth"] * C.CLOCK - 1e-9)
        exposed = (g.fin[collective] - max(g.fin[d] for d in c["deps"])) * C.CLOCK
        out[label] = dict(node=collective, mode=1, words=words, prod=producer,
                          issue=issue, depth=depth, order="uniform", link="t1",
                          model_exposed=exposed, on_path=0,
                          consumer="blocking full-vector consumer after the gather")
    return out


def build(scratch: Path) -> dict:
    patterns = patterns_from_design_point()
    C.PATTERNS.update(patterns)
    lp = C.link_params()
    rows = []
    # Sweep receiver depth; QTX=64 is the stage bench's bounded transmit queue.
    for name in ("act", "y"):
        for depth in (16, 32, 64, 128):
            case = dict(name=f"rowsplit_{name}_d{depth}", pattern=name,
                        depth=depth, qtx=64)
            rows.append(C.run_case(scratch, case, lp))
    # A 512-word producer queue tests whether the 64-word queue is the cause
    # of the activation producer's stall. This is a sensitivity, not the die's
    # built queue size.
    rows.append(C.run_case(scratch,
                           dict(name="rowsplit_act_d64_q512", pattern="act", depth=64, qtx=512), lp))
    for row in rows:
        assert row["passed"] and row["mismatches"] == row["out_err"] == row["timeout"] == 0
        assert all(fault == 0 for fault in row["faults"])
    sources = ("tools/rtl_v41_tp_rowsplit_collectives.py",
               "tools/v41_tp_exact_reprice.py", "tools/arch_lanes_v41.py",
               "tools/decode_critical_path.py", "tools/rtl_v41_stage_collective_campaign.py",
               "rtl/rom/ot_rom_oneshot_allreduce.sv", "rtl/proto/ot_fp32_add_rne_pipe.sv",
               "rtl/test/tb_v41_stage_collective.sv")
    pins = {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in sources}
    summary = {}
    for name in patterns:
        subset = [r for r in rows if r["pattern"] == name]
        best = min(subset, key=lambda r: r["exposed_tail_cycles"])
        summary[name] = dict(best_depth=best["rx_depth_words"],
                             measured_tail_cycles=best["exposed_tail_cycles"],
                             model_overlap_exposed_cycles=patterns[name]["model_exposed"],
                             min_no_stall_depth=min((r["rx_depth_words"] for r in subset
                                                     if r["producer_stall_cycles"] == 0), default=None),
                             measured_best_minus_model_cycles=best["exposed_tail_cycles"]
                             - patterns[name]["model_exposed"])
    return dict(schema="v41_tp_rowsplit_collectives_v1", source_sha256=pins,
                historical_width_reference=dict(commit="159e179c", die_CL_LANES=16,
                                                note="die top is not instantiated by this standalone stage bench"),
                scope="one-shot gather RTL with behavioural T1 and producer schedule from current model; no die/full-shape throughput claim",
                link=lp, patterns=patterns, cases=rows, summary=summary)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scratch", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    args.scratch.mkdir(parents=True, exist_ok=True)
    rec = build(args.scratch)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(rec, indent=2, sort_keys=True) + "\n")
    print(json.dumps(rec["summary"], indent=2))


if __name__ == "__main__":
    main()
