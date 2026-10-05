#!/usr/bin/env python3
"""Adopted-link GW4 stage with the double-buffered rank-major VM transpose."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

import rtl_v41_tp_rowsplit_die_collectives as D
import rtl_v41_collective_levers_campaign as L
import rtl_v41_stage_collective_campaign as B

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/rtl/v41_collective_gw4_banked.json"
TB = ROOT / "rtl/test/tb_v41_tp_rowsplit_gw4_banked.sv"
TRANSPOSE = ROOT / "rtl/chip/ot_chip_v41x_coll_transpose.sv"


def run(scratch: Path) -> dict:
    B.PATTERNS.update(D.patterns_from_design_point())
    link = B.link_params()
    old_tb, old_top, old_sources = L.TB, L.top_params, L.sources
    L.TB = TB
    L.sources = lambda: old_sources() + [TRANSPOSE]
    L.LEVERS["relay_add3_gw4_banked"] = (1, 3, 4)

    def params(case: dict, lp: dict):
        _, p = old_top(case, lp)
        p.update(PUSHW=1, PAIRWISE=1)
        return "tb_v41_stage_collective_px_gw4_bank", p

    L.top_params = params
    try:
        cases = []
        for pattern in ("act", "y"):
            case = dict(name=f"{pattern}_d256_q2_gw4_pairwise_bank", pattern=pattern,
                        lever="relay_add3_gw4_banked", depth=256, qtx=2, lanes=16,
                        order="blocked")
            cases.append(L.run_case(scratch, case, link))
    finally:
        L.TB, L.top_params, L.sources = old_tb, old_top, old_sources
        del L.LEVERS["relay_add3_gw4_banked"]
    for case in cases:
        if not case["passed"] or case["mismatches"] or case["out_err"] or case["timeout"] or any(case["faults"]):
            raise AssertionError(f"GW4 banked stage failed: {case['case']}")
    paths = (
        "tools/rtl_v41_collective_gw4_banked.py", "tools/rtl_v41_tp_rowsplit_die_collectives.py",
        "tools/rtl_v41_tp_rowsplit_collectives.py", "tools/rtl_v41_collective_levers_campaign.py",
        "tools/rtl_v41_stage_collective_campaign.py", "rtl/test/tb_v41_tp_rowsplit_gw4_banked.sv",
        "rtl/chip/ot_chip_v41x_coll_transpose.sv", "rtl/rom/ot_rom_oneshot_px.sv",
        "rtl/hdc/ot_hdc_fastfp.sv", "rtl/proto/ot_fp32_add_rne_pipe.sv",
        "tools/hdc_golden.py", "results/arch/v41_lanes.json",
    )
    summary = {c["pattern"]: dict(words_per_die=c["words_per_die"],
                                  banked_tail_cycles=c["exposed_tail_cycles"],
                                  producer_stall_cycles=c["producer_stall_cycles"])
               for c in cases}
    return dict(schema="v41_collective_gw4_banked_v1",
                scope="exact 64B pairwise one-shot engine, adopted behavioural links and double-buffered transpose; bank sink accepts four words/cycle; no die token or route claim",
                contract=dict(N=4, FLIT_BYTES=64, CL_DEPTH=256, RELAY=1, ADD_LAT=3,
                              PAIRWISE=1, GW=4, OUT_BP=1, PUSHW=1, QTX=2,
                              blocked_COLL_v1=True, bank_write_words_per_cycle=4,
                              bank_write_word_bits=512, bank_write_bus_bits=2048,
                              full_shape_transpose_OUT_PIPE=1,
                              full_width_physical_route="open"),
                verilator=subprocess.check_output([shutil.which("verilator"), "--version"], text=True).strip(),
                source_sha256={p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in paths},
                link=link, cases=cases, summary=summary)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scratch", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    args.scratch.mkdir(parents=True, exist_ok=True)
    record = run(args.scratch)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    print(json.dumps(record["summary"], indent=2))


if __name__ == "__main__":
    main()
