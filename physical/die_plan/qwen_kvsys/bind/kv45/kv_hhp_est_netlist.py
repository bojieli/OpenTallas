#!/usr/bin/env python3
"""CODEX-PICKUP-KV 2026-11-01 HHP joint event (COORD Q3 / 12.28b): the four head parents (pc_{E,W}{N,S}_0) split the EST
broadcast of their group tile slg_<Q>_4 (qkd_kvs_grp_h_r2c) into two same-edge copies.

One xe1[0] flop cannot reach all four child captures of the parent within 405 um (actual source radius 415.128 um,
CODEX-LOG HHP).  qkd_kvs_grp_h_r2c (group_r2c_native.sv) now has a parallel EST flop xe1b (same D xe0[0], same edge,
0 added cycles) on its new output y__est__0_1_b.  This netlist edit is the die connectivity of that event, nothing else:

  slg_<Q>_4  .y__est__0_1_b(n_ks_slg_<Q>_4__y__est__0_1_b[0])           (new wire, declared next to the original)
  kvpc_<Q>_0 / kvpc_<Q>_1  .x__est__0_1  <- n_ks_slg_<Q>_4__y__est__0_1_b[0]   (lower pair: HHP head + PC1)
  kvpc_<Q>_2 / kvpc_<Q>_3  .x__est__0_1  <- n_ks_slg_<Q>_4__y__est__0_1[0]     (upper pair: unchanged)

Applied to BOTH die_bound_native_mission.v.gz and die_bound_native_mission_lc.v.gz (the DIE-KV-19 pv-lc derivation
touches only pv slice lines, so kv_pv_lc_netlist.py --check stays exact).

  kv_hhp_est_netlist.py            rewrite both netlists in place (idempotent)
  kv_hhp_est_netlist.py --check    fail unless both committed netlists carry the event
"""
import gzip
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
FILES = [HERE / "die_bound_native_mission.v.gz", HERE / "die_bound_native_mission_lc.v.gz"]
QUADS = ("EN", "WN", "ES", "WS")


def derive(text):
    lines = text.split("\n")
    n = {"wire": 0, "slg": 0, "kvpc": 0}
    out = []
    for line in lines:
        out.append(line)
        for q in QUADS:
            net = f"n_ks_slg_{q}_4__y__est__0_1"
            if line.strip() == f"wire [0:0] {net};":
                out.append(line.replace(net, net + "_b"))
                n["wire"] += 1
    for k, line in enumerate(out):
        for q in QUADS:
            net = f"n_ks_slg_{q}_4__y__est__0_1"
            if re.match(rf"^\s*qkd_kvs_grp_h_r2c slg_{q}_4 \(", line):
                old = f".y__est__0_1({net}[0])"
                assert line.count(old) == 1, (q, "slg")
                line = line.replace(old, old + f", .y__est__0_1_b({net}_b[0])")
                n["slg"] += 1
            elif re.match(rf"^\s*\S+ kvpc_{q}_[01] \(", line):
                old = f".x__est__0_1({net}[0])"
                assert line.count(old) == 1, (q, "kvpc", line[:80])
                line = line.replace(old, f".x__est__0_1({net}_b[0])")
                n["kvpc"] += 1
        out[k] = line
    assert n == {"wire": 4, "slg": 4, "kvpc": 8}, n
    return "\n".join(out)


def applied(text):
    return all(f"n_ks_slg_{q}_4__y__est__0_1_b" in text for q in QUADS)


if __name__ == "__main__":
    bad = []
    for f in FILES:
        txt = gzip.decompress(f.read_bytes()).decode()
        if "--check" in sys.argv:
            if not applied(txt):
                bad.append(f)
            continue
        if applied(txt):
            print("already applied", f)
            continue
        f.write_bytes(gzip.compress(derive(txt).encode(), mtime=0))
        print("wrote", f)
    sys.exit(f"STALE {bad}" if bad else 0)
