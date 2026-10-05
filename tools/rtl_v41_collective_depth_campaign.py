#!/usr/bin/env python3
"""Measure the full-shape die's receive-credit depth on exact TP gathers.

This uses the same 64-byte flit, behavioural T1/UCIe links and one-word VM
producer as the adopted die-width campaign.  It does not claim a routed die.
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
OUT = ROOT / "results/rtl/v41_collective_depth_campaign.json"


def run(scratch: Path) -> dict:
    B.PATTERNS.update(D.patterns_from_design_point())
    link = B.link_params()
    original = L.top_params
    original_tb = L.TB
    L.TB = D.TB

    def die_params(case: dict, lp: dict):
        top, params = original(case, lp)
        params["PUSHW"] = 1
        params["PAIRWISE"] = 1
        return top, params

    L.top_params = die_params
    try:
        cases = []
        for pattern in ("act", "y"):
            for depth in (16, 128):
                case = dict(name=f"{pattern}_d{depth}_q2_blocked_pairwise",
                            pattern=pattern, lever="relay_add3", depth=depth,
                            qtx=2, lanes=16, order="blocked")
                cases.append(L.run_case(scratch, case, link))
    finally:
        L.top_params = original
        L.TB = original_tb
    for case in cases:
        if not case["passed"] or case["mismatches"] or case["out_err"] or case["timeout"] or any(case["faults"]):
            raise AssertionError(f"collective exact gate failed: {case['case']}")
    pins = (
        "tools/rtl_v41_collective_depth_campaign.py",
        "tools/rtl_v41_tp_rowsplit_die_collectives.py",
        "tools/rtl_v41_tp_rowsplit_collectives.py",
        "tools/rtl_v41_collective_levers_campaign.py",
        "tools/rtl_v41_stage_collective_campaign.py",
        "rtl/test/tb_v41_tp_rowsplit_px.sv",
        "rtl/rom/ot_rom_oneshot_px.sv",
        "rtl/hdc/ot_hdc_fastfp.sv",
        "rtl/proto/ot_fp32_add_rne_pipe.sv",
        "tools/hdc_golden.py",
        "results/arch/v41_lanes.json",
    )
    by_pattern = {}
    for pattern in ("act", "y"):
        old = next(c for c in cases if c["pattern"] == pattern and c["rx_depth_words"] == 16)
        new = next(c for c in cases if c["pattern"] == pattern and c["rx_depth_words"] == 128)
        outputs = 4 * new["words_per_die"]
        by_pattern[pattern] = dict(
            input_words_per_die=new["words_per_die"], output_words_per_die=outputs,
            old_tail_cycles=old["exposed_tail_cycles"], selected_tail_cycles=new["exposed_tail_cycles"],
            saved_cycles=old["exposed_tail_cycles"] - new["exposed_tail_cycles"],
            output_port_minimum_cycles=outputs,
            selected_first_to_last_cycles=new["consumer_last_word_cycle"] - new["consumer_first_word_cycle"] + 1,
        )
    bits_per_record = 512 + 3 + 32
    return dict(
        schema="v41_collective_depth_campaign_v1",
        scope="one-shot engine and behavioural links; stage timing stub, die and DMA not instantiated; no full token or P&R claim",
        source_sha256={p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in pins},
        contract=dict(N=4, FLIT_BYTES=64, CL_LANES=16, RELAY=1, ADD_LAT=3,
                      PAIRWISE=1, GW=1, PUSHW=1, QTX=2, blocked_COLL_v1=True,
                      selected_full_shape_CL_DEPTH=128, reduced_CL_DEPTH=16,
                      die_default_checked_by_test=True,
                      receive_fifo_bits_at_16=4 * 16 * bits_per_record,
                      receive_fifo_bits_at_128=4 * 128 * bits_per_record),
        link=link, cases=cases, summary=by_pattern,
    )


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
