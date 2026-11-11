#!/usr/bin/env python3
"""DIE-QC-97 STM-DQ 11-10 plan event (COORD adopted 161d17842f0): opt the 11 QC stm types into OT_QC_STMDQ.

QC-FAIL-22: slw_stm_v1__cl05fc43f7__cl389df4e9 a22 routed but not signed off.  Its we_c[0] -> u_stream.dupq path is
-669.7 ps TT and its u_rl.rst -> tag[19] recovery path is -225.2 ps.  The cause is a placement detour, not a die-wide
gather: decoder copy we_c[0] also fed the beat fault next to the xw_addr pins.  rtl/qwen_dv/qfd_dv_stream_tile.sv
STM-DQ, under `ifdef OT_QC_STMDQ, adds:
  (a) a kept beat-fault enable root we_b;
  (b) dupq as 8 registered partial ORs, reduced after the register;
  (c) the tile lands rst_n itself in 7 kept two-stage copies, one per reset group, with qfd_dv_s6_stm passing the raw
      rst_n to u_stream (the s8_ce chain-END se0 copies are generated from these sources).
No port edge changes, so there is no lane, latency or pin change.  The type's verilog_defines is the one source profile
for kit synthesis, RTL lint and the LEC gold reader (gen_phys.type_verilog_defines), so the kit RTL and its LEC see the
same form.
This event only appends "OT_QC_STMDQ" to partition_types[t].verilog_defines of the 11 stm types below; no other field
changes.  It refuses a type that already carries the define (merge by hand) and a plan without one of the types.
EQ gate (define-on vs default): see rtl/test/qwen_dv/static_stream/stmdq_eq.ys (yosys equiv_induct of the s6_stm stream
half, default vs OT_QC_STMDQ, for qfd_dv_stream_tile and qfd_dv_stream_tile_se0) and run_tile_stmdq.sh (old-vs-new
bench with must-fail mutants).
    delta_stmdq_1110.py PLAN.json OUT.json   -> prints {types, sha256_in, sha256_out}
"""
import argparse
import hashlib
import json
from pathlib import Path

DEFINE = "OT_QC_STMDQ"
TYPES = (
    "slw_stm_v1__cl05fc43f7__cl389df4e9", "slw_stm_v1__cl05fc43f7__cl2086fa2c", "slw_stm_v1__cle34a73c3",
    "slw_stm_v2__cl1ca9c415", "slw_stm_v2__cl9beb65e6", "slw_stm_v3",
    "sle_stm_v1__cl27746664", "sle_stm_v1__clbe630b9c", "sle_stm_v2__cl7b3062fa", "sle_stm_v2__cl55be2264",
    "sle_stm_v3",
)


def apply(raw):
    pt = raw["partition_types"]
    missing = [t for t in TYPES if t not in pt]
    if missing:
        raise SystemExit(f"STMDQ: plan lacks stm types {missing}")
    have = [t for t in TYPES if DEFINE in (pt[t].get("verilog_defines") or [])]
    if have:
        raise SystemExit(f"STMDQ: {DEFINE} already present on {have} (merge by hand)")
    for t in TYPES:
        pt[t]["verilog_defines"] = list(pt[t].get("verilog_defines") or []) + [DEFINE]
    return raw


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("input")
    p.add_argument("output")
    a = p.parse_args()
    src = Path(a.input).read_bytes()
    raw = apply(json.loads(src))
    out = (json.dumps(raw, separators=(",", ":")) + "\n").encode()
    Path(a.output).write_bytes(out)
    print(json.dumps({"types": len(TYPES), "define": DEFINE, "sha256_in": hashlib.sha256(src).hexdigest(),
                      "sha256_out": hashlib.sha256(out).hexdigest()}))


if __name__ == "__main__":
    main()
