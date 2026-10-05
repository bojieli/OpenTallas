#!/usr/bin/env python3
"""Exact V4.1 64-byte GW4 gather-engine stage gate.

The consumer accepts four rank words per cycle.  A separate DMA/tile gate must
establish the corresponding four-bank VM write path before this is a die claim.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import rtl_v41_tp_rowsplit_die_collectives as D
import rtl_v41_collective_levers_campaign as L
import rtl_v41_stage_collective_campaign as B

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/rtl/v41_collective_gw4_campaign.json"
BASE = ROOT / "results/rtl/v41_collective_depth_campaign.json"


def run(scratch: Path) -> dict:
    B.PATTERNS.update(D.patterns_from_design_point())
    link = B.link_params()
    old_tb, old_top = L.TB, L.top_params
    L.TB = D.TB
    L.LEVERS["relay_add3_gw4"] = (1, 3, 4)

    def params(case: dict, lp: dict):
        top, p = old_top(case, lp)
        p["PUSHW"] = 1
        p["PAIRWISE"] = 1
        return top, p

    L.top_params = params
    try:
        cases = []
        for pattern in ("act", "y"):
            case = dict(name=f"{pattern}_d256_q2_gw4_pairwise", pattern=pattern,
                        lever="relay_add3_gw4", depth=256, qtx=2, lanes=16,
                        order="blocked")
            cases.append(L.run_case(scratch, case, link))
    finally:
        L.TB, L.top_params = old_tb, old_top
        del L.LEVERS["relay_add3_gw4"]
    for c in cases:
        if not c["passed"] or c["mismatches"] or c["out_err"] or c["timeout"] or any(c["faults"]):
            raise AssertionError(f"GW4 exact gate failed: {c['case']}")
    base = json.loads(BASE.read_text())
    assert base["contract"]["selected_full_shape_CL_DEPTH"] == 128
    assert base["contract"]["GW"] == 1
    summary = {}
    for c in cases:
        p = c["pattern"]
        b = base["summary"][p]
        summary[p] = dict(words_per_die=c["words_per_die"], output_words_per_die=4*c["words_per_die"],
                          gw1_depth128_tail_cycles=b["selected_tail_cycles"],
                          gw4_depth256_tail_cycles=c["exposed_tail_cycles"],
                          saved_cycles=b["selected_tail_cycles"]-c["exposed_tail_cycles"],
                          producer_stall_cycles=c["producer_stall_cycles"])
    paths = (
        "tools/rtl_v41_collective_gw4_campaign.py", "tools/rtl_v41_tp_rowsplit_die_collectives.py",
        "tools/rtl_v41_tp_rowsplit_collectives.py", "tools/rtl_v41_collective_levers_campaign.py",
        "tools/rtl_v41_stage_collective_campaign.py", "rtl/test/tb_v41_tp_rowsplit_px.sv",
        "rtl/rom/ot_rom_oneshot_px.sv", "rtl/hdc/ot_hdc_fastfp.sv",
        "rtl/proto/ot_fp32_add_rne_pipe.sv", "tools/hdc_golden.py",
        "results/arch/v41_lanes.json", "results/rtl/v41_collective_depth_campaign.json",
    )
    return dict(schema="v41_collective_gw4_campaign_v1",
                scope="exact 64B one-shot engine with behavioural links and four-word accepting consumer; DMA/VM banking not instantiated",
                contract=dict(N=4, FLIT_BYTES=64, CL_DEPTH=256, RELAY=1, ADD_LAT=3,
                              PAIRWISE=1, GW=4, OUT_BP=0, PUSHW=1, QTX=2, blocked_COLL_v1=True),
                source_sha256={p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths},
                link=link, cases=cases, summary=summary)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scratch", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    args.scratch.mkdir(parents=True, exist_ok=True)
    rec = run(args.scratch)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(rec, indent=2, sort_keys=True) + "\n")
    print(json.dumps(rec["summary"], indent=2))


if __name__ == "__main__":
    main()
