#!/usr/bin/env python3
"""Measure V4.1 TP row-split gathers on the adopted 64-byte die collective.

The producer remains a stage timing stub. The engine, relay/add3 parameters,
CL_DEPTH=16, and one-word VM producer port match the current die RTL. Link
latencies and bandwidth remain behavioural. This is a calibration input, not
full-shape token or routed-die throughput.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import rtl_v41_stage_collective_campaign as B  # noqa: E402

B.LANES = 16
B.WORD_B = 64

import rtl_v41_collective_levers_campaign as L  # noqa: E402
from rtl_v41_tp_rowsplit_collectives import patterns_from_design_point  # noqa: E402

OUT = ROOT / "results/rtl/v41_tp_rowsplit_die_collectives.json"
TB = ROOT / "rtl/test/tb_v41_tp_rowsplit_px.sv"


def build(scratch: Path) -> dict:
    pats = patterns_from_design_point()
    B.PATTERNS.update(pats)
    assert (L.LANES, L.WORD_B) == (16, 64)
    lp = B.link_params()
    original_top_params = L.top_params
    original_tb = L.TB
    L.TB = TB

    def top_params_one_vm_word(case, link):
        top, params = original_top_params(case, link)
        params["PUSHW"] = 1
        params["PAIRWISE"] = 1
        return top, params

    L.top_params = top_params_one_vm_word
    try:
        cases = []
        for pattern in ("act", "y"):
            # COLL v1 blocks instruction issue: all local VM words have been
            # produced before the DMA starts. The blocked schedule is the
            # adopted point; uniform is an overlap sensitivity only.
            for depth, qtx, order in ((16, 2, "blocked"), (16, 2, "uniform")):
                case = dict(name=f"die_{pattern}_d{depth}_q{qtx}_{order}", pattern=pattern,
                            lever="relay_add3", depth=depth, qtx=qtx, lanes=16,
                            order=order)
                cases.append(L.run_case(scratch, case, lp))
    finally:
        L.top_params = original_top_params
        L.TB = original_tb
    for case in cases:
        assert case["passed"] and case["mismatches"] == case["out_err"] == case["timeout"] == 0
        assert all(fault == 0 for fault in case["faults"])
    source_paths = ("tools/rtl_v41_tp_rowsplit_die_collectives.py",
                    "tools/rtl_v41_tp_rowsplit_collectives.py", "tools/v41_tp_exact_reprice.py",
                    "tools/rtl_v41_collective_levers_campaign.py",
                    "tools/rtl_v41_stage_collective_campaign.py",
                    "rtl/rom/ot_rom_oneshot_px.sv", "rtl/hdc/ot_hdc_fastfp.sv",
                    "rtl/proto/ot_fp32_add_rne_pipe.sv",
                    "rtl/test/tb_v41_tp_rowsplit_px.sv",
                    "rtl/test/tb_v41_stage_hop_px.sv",
                    "tools/hdc_golden.py", "results/arch/v41_lanes.json",
                    "tools/arch_lanes_v41.py", "tools/decode_critical_path.py")
    pins = {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in source_paths}
    summary = {}
    for pattern in ("act", "y"):
        row = next(x for x in cases if x["pattern"] == pattern and x["rx_depth_words"] == 16
                   and x["order"] == "blocked")
        summary[pattern] = dict(measured_tail_cycles=row["exposed_tail_cycles"],
                                model_overlap_exposed_cycles=pats[pattern]["model_exposed"],
                                gap_cycles=row["exposed_tail_cycles"] - pats[pattern]["model_exposed"],
                                producer_stall_cycles=row["producer_stall_cycles"],
                                port_words_per_die=pats[pattern]["words"])
    return dict(schema="v41_tp_rowsplit_die_collectives_v1", source_sha256=pins,
                scope="adopted-width one-shot RTL and behavioural UCIe/T1 link with blocked COLL-v1 producer; no full-shape or P&R claim",
                die_contract=dict(CL_LANES=16, flit_bytes=64, CL_DEPTH=16,
                                  DMA_VM_words_per_cycle=1, DMA_skid_words=2,
                                  RELAY=1, ADD_LAT=3, PAIRWISE=1, GW=1,
                                  reference_commit="dc4ee8aa",
                                  note="die top and CDMA are not instantiated; QTX2/PUSHW1 are timing stubs of their ports"),
                link=lp, patterns=pats, cases=cases, summary=summary)


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
