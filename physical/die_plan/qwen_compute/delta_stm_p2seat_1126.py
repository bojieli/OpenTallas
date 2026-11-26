#!/usr/bin/env python3
"""QC-INT-R2-HCSETUP 11-26 plan delta (class C-LEG405 intra-core, private candidate on C9): opt the STM types with measured
p2l tree-leg failures into OT_QC_STM_P2SEAT (rtl/qwen_dv/qfd_dv_stream_tile.sv, qfd_dv_s8_ce.sv): the four far P2 leaves
(ie_e / ie_w groups 73, 74) take a complete tree of their own instead of sharing trees 2 and 5 with near leaves.
Zero latency: no port, lane, pin or edge change (tile-level lockstep bench, run_tile_p2seat.sh).  Evidence:
sle_stm_v2 cl7b3062fa TT -53.97 (p2l[74] leg 540..582 um), cl55be2264 TT -78.2, sle_stm_v3 -50.94 / -59.41 (QC-STM-FAM).
Only appends the define; refuses a type that already carries it or a plan without the type.
    delta_stm_p2seat_1126.py PLAN.json OUT.json
"""
import argparse, hashlib, json
from pathlib import Path

DEFINE = "OT_QC_STM_P2SEAT"
TYPES = ("sle_stm_v2__cl7b3062fa", "sle_stm_v2__cl55be2264", "sle_stm_v3")
HC_DEFINE = "OT_QC_XH_SPLIT_FAULT"   # xhead3 SPLIT_STICKY_FAULT = 1 (C-CONE-DEPTH), sle_hc0 cl38badc56 only (ruling 09:58)
HC_TYPE = "sle_hc0__cl929603c0__cl38badc56"


def apply(raw):
    pt = raw["partition_types"]
    missing = [t for t in TYPES if t not in pt]
    if missing:
        raise SystemExit(f"P2SEAT: plan lacks stm types {missing}")
    have = [t for t in TYPES if DEFINE in (pt[t].get("verilog_defines") or [])]
    if have:
        raise SystemExit(f"P2SEAT: {DEFINE} already present on {have}")
    for t in TYPES:
        pt[t]["verilog_defines"] = list(pt[t].get("verilog_defines") or []) + [DEFINE]
    if HC_TYPE not in pt or HC_DEFINE in (pt[HC_TYPE].get("verilog_defines") or []):
        raise SystemExit(f"P2SEAT: {HC_TYPE} missing or already carries {HC_DEFINE}")
    pt[HC_TYPE]["verilog_defines"] = list(pt[HC_TYPE].get("verilog_defines") or []) + [HC_DEFINE]
    return raw


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("input"); p.add_argument("output")
    a = p.parse_args()
    src = Path(a.input).read_bytes()
    out = (json.dumps(apply(json.loads(src)), separators=(",", ":")) + "\n").encode()
    Path(a.output).write_bytes(out)
    print(json.dumps({"types": len(TYPES) + 1, "define": DEFINE, "sha256_in": hashlib.sha256(src).hexdigest(),
                      "sha256_out": hashlib.sha256(out).hexdigest()}))


if __name__ == "__main__":
    main()
