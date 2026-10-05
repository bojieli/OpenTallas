#!/usr/bin/env python3
"""Bound six-position V4.1 TP gathers on the current 64-byte pairwise engine.

The six activations are already in VM when COLL begins.  The two schedules
exercise one fused descriptor and six serial descriptors; neither claims
that the full-shape MTP program emits either schedule yet.  The producer,
UCIe and T1 remain stage timing stubs.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import rtl_v41_tp_rowsplit_die_collectives as D

L, B = D.L, D.B
ROOT = D.ROOT
OUT = ROOT / "results/rtl/v41_tp_rowsplit_mtp_collectives.json"


def build(scratch: Path) -> dict:
    base = D.patterns_from_design_point()
    assert (base["act"]["words"], base["y"]["words"]) == (266, 80)
    B.PATTERNS.update(base)
    lp = B.link_params()
    old_tb, old_top, old_maxw = L.TB, L.top_params, L.MAXW
    L.TB = D.TB

    def top_params(case, link):
        top, params = old_top(case, link)
        params.update(PUSHW=1, PAIRWISE=1, MAXW=2048 if case["fused"] else 512)
        return top, params

    L.top_params = top_params
    cases = []
    try:
        for pattern in ("act", "y"):
            fused = f"{pattern}_mtp_fused"
            B.PATTERNS[fused] = dict(base[pattern], words=base[pattern]["words"] * 6)
            L.MAXW = 2048
            cases.append(L.run_case(scratch, dict(name=f"{fused}_d128", pattern=fused,
                                               lever="relay_add3", depth=128, qtx=2,
                                               lanes=16, order="blocked", fused=True), lp))
            L.MAXW = 512
            for position in range(6):
                cases.append(L.run_case(scratch, dict(name=f"{pattern}_mtp_serial_{position}_d128",
                                                   pattern=pattern, lever="relay_add3", depth=128,
                                                   qtx=2, lanes=16, order="blocked", fused=False), lp))
    finally:
        L.TB, L.top_params, L.MAXW = old_tb, old_top, old_maxw
    assert all(c["passed"] and c["mismatches"] == c["out_err"] == c["timeout"] == 0
               and not any(c["faults"]) for c in cases)
    summary = {}
    for pattern in ("act", "y"):
        fused = next(c for c in cases if c["case"] == f"{pattern}_mtp_fused_d128")
        serial = [c for c in cases if c["case"].startswith(f"{pattern}_mtp_serial_")]
        assert len(serial) == 6
        summary[pattern] = dict(local_flits_per_die=base[pattern]["words"],
                                fused_local_flits_per_die=fused["words_per_die"],
                                fused_exposed_tail_cycles=fused["exposed_tail_cycles"],
                                serial_six_exposed_tail_cycles=sum(c["exposed_tail_cycles"] for c in serial),
                                one_vm_write_per_cycle_floor=4 * fused["words_per_die"])
    sources = ("tools/rtl_v41_tp_rowsplit_mtp_collectives.py",
               "tools/rtl_v41_tp_rowsplit_die_collectives.py",
               "tools/rtl_v41_tp_rowsplit_collectives.py",
               "tools/rtl_v41_collective_levers_campaign.py",
               "tools/rtl_v41_stage_collective_campaign.py",
               "rtl/test/tb_v41_tp_rowsplit_px.sv", "rtl/test/tb_v41_stage_hop_px.sv",
               "rtl/rom/ot_rom_oneshot_px.sv", "rtl/hdc/ot_hdc_fastfp.sv",
               "rtl/proto/ot_fp32_add_rne_pipe.sv",
               "tools/hdc_golden.py", "tools/arch_lanes_v41.py",
               "tools/decode_critical_path.py", "results/arch/v41_lanes.json")
    pins = {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in sources}
    return dict(schema="v41_tp_rowsplit_mtp_collectives_v1", source_sha256=pins,
                scope="six-position payload-matched blocked stage RTL sensitivity; MTP program schedule, real producer and routed links unverified",
                contract=dict(CL_LANES=16, flit_bytes=64, CL_DEPTH=128, DMA_VM_words_per_cycle=1,
                              PAIRWISE=1, PUSHW=1, QTX=2, m=6),
                link=lp, patterns={k: base[k] for k in ("act", "y")}, cases=cases, summary=summary)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scratch", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    args.scratch.mkdir(parents=True, exist_ok=True)
    rec = build(args.scratch)
    args.out.write_text(json.dumps(rec, indent=2, sort_keys=True) + "\n")
    print(json.dumps(rec["summary"], indent=2))


if __name__ == "__main__":
    main()
