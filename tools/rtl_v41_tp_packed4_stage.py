#!/usr/bin/env python3
"""Measure packed4-size V4.1 gather packets on the existing GW1 engine.

This checks descriptor length, credits and link timing for packed4-sized
payloads.  Inputs are arbitrary exact 32-bit words; core packing, unpacking
and full-shape token arithmetic are outside this gate.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import rtl_v41_tp_rowsplit_die_collectives as D

ROOT, B, L = D.ROOT, D.B, D.L
OUT = ROOT / "results/rtl/v41_tp_packed4_stage.json"


def build(scratch: Path):
    base = D.patterns_from_design_point()
    assert base["act"]["words"] == 266 and base["y"]["words"] == 80
    words = {"act": 77, "y": 40}
    # 7 experts x padded 176 packed4 entries; 2 BF16 values per y entry.
    assert 7 * 176 // 16 == words["act"] and (1280 // 2) // 16 == words["y"]
    for kind, count in words.items():
        B.PATTERNS[f"packed_{kind}"] = dict(base[kind], words=count)
        B.PATTERNS[f"packed_{kind}_mtp"] = dict(base[kind], words=6 * count)
    lp = B.link_params()
    old_tb, old_top = L.TB, L.top_params
    L.TB = D.TB

    def top_params(case, link):
        top, params = old_top(case, link)
        params.update(PUSHW=1, PAIRWISE=1)
        return top, params

    L.top_params = top_params
    cases = []
    try:
        for kind in ("act", "y"):
            for pattern in (f"packed_{kind}", f"packed_{kind}_mtp"):
                cases.append(L.run_case(scratch, dict(name=pattern, pattern=pattern,
                                                   lever="relay_add3", depth=128, qtx=2,
                                                   lanes=16, order="blocked"), lp))
            for i in range(6):
                cases.append(L.run_case(scratch, dict(name=f"packed_{kind}_serial_{i}",
                                                   pattern=f"packed_{kind}", lever="relay_add3",
                                                   depth=128, qtx=2, lanes=16, order="blocked"), lp))
    finally:
        L.TB, L.top_params = old_tb, old_top
    assert len(cases) == 16
    assert all(c["passed"] and c["mismatches"] == c["out_err"] == c["timeout"] == 0
               and not any(c["faults"]) for c in cases)
    summary = {}
    for kind in ("act", "y"):
        ar = next(c for c in cases if c["case"] == f"packed_{kind}")
        fused = next(c for c in cases if c["case"] == f"packed_{kind}_mtp")
        serial = [c for c in cases if c["case"].startswith(f"packed_{kind}_serial_")]
        assert len(serial) == 6
        summary[kind] = dict(local_flits_per_die=words[kind], ar_tail_cycles=ar["exposed_tail_cycles"],
                             ar_producer_stall_cycles=ar["producer_stall_cycles"],
                             mtp_fused_flits_per_die=6 * words[kind],
                             mtp_fused_tail_cycles=fused["exposed_tail_cycles"],
                             mtp_fused_producer_stall_cycles=fused["producer_stall_cycles"],
                             mtp_serial_six_tail_cycles=sum(c["exposed_tail_cycles"] for c in serial),
                             ar_output_port_floor=4 * words[kind],
                             mtp_output_port_floor=24 * words[kind])
    pins = ("tools/rtl_v41_tp_packed4_stage.py", "tools/rtl_v41_tp_rowsplit_die_collectives.py",
            "tools/rtl_v41_tp_rowsplit_collectives.py", "tools/rtl_v41_collective_levers_campaign.py",
            "tools/rtl_v41_stage_collective_campaign.py", "rtl/test/tb_v41_tp_rowsplit_px.sv",
            "rtl/rom/ot_rom_oneshot_px.sv", "rtl/hdc/ot_hdc_fastfp.sv",
            "rtl/proto/ot_fp32_add_rne_pipe.sv", "tools/hdc_golden.py",
            "tools/arch_lanes_v41.py", "tools/decode_critical_path.py",
            "results/arch/v41_lanes.json")
    return dict(schema="v41_tp_packed4_stage_v1",
                scope="exact one-shot timing for packed4-sized arbitrary words; no core packing, emitter or full-token claim",
                source_sha256={p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in pins},
                contract=dict(flits_B=64, CL_LANES=16, CL_DEPTH=128, QTX=2, PUSHW=1,
                              PAIRWISE=1, GW=1, blocked_COLL_v1=True),
                link=lp, cases=cases, summary=summary)


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
