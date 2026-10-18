#!/usr/bin/env python3
"""PL-KVHOST (PARENTS-LANDED 10-18): region-plan check for the KV host-root cluster qkd_hr_cluster.

Uses tools/landed_parent/lp.py's parser on the generated wires-only parent and reports, for a candidate split of the
CORE clock family into regions, every same-family cross-region net (would be LANDED: +3 edges, D x W ring flops) and
every cross-region 2-cycle (a loop lp.py cannot keep on the flat schedule).  Cross-FAMILY nets are not counted: they
already pass through the 4 CDC leaves (cdc_host, cdc_pc, ingest_qm) and stay CDC.

  python3 tools/qwen_kv_die/host_cluster/region_plan_check.py [--hi u_core_peer,u_core_prompt] [--json OUT]
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools/landed_parent"))
import lp  # noqa: E402

H = "rtl/qwen_sys/host_cluster_20261017/"
KIDS = [H + f"qkd_hr_{c}.v" for c in
        "cdc_host cdc_pc core_guard core_order core_peer core_prompt core_queue core_tx ingest_qm".split()]
KIDS += ["rtl/physical/ot_qfd_link_adp512_split.sv", "rtl/qwen_sys/host_20261013/qkd_host_rx_class_admission_rr.sv",
         "rtl/qwen_sys/host_20261013/qkd_host_rx_pad5.sv"]
# clock family of each child's CORE-relevant side (multi-family CDC leaves are core on their core face)
FAMILY = {"u_core_*": "core", "u_rank__u_control__u_packet__u_rx": "core", "u_cdc_*": "cdc", "u_ingest_qm": "cdc",
          "u_rank__u_adapter__*": "phy", "u_rank__u_phy__u_pad": "phy"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hi", default="u_core_peer,u_core_prompt", help="core children in the second core region")
    ap.add_argument("--json")
    a = ap.parse_args()
    hi = a.hi.split(",")
    spec = dict(top="qkd_hr_cluster", sources=[H + "qkd_hr_cluster.v"], child_sources=KIDS, out_dir="/tmp/unused",
                clock_ports=["ck_core", "ck_host", "ck_ingest", "ck_phy_fam", "ck_phy"],
                clock_pins=["ck", "clk", "ck_core", "ck_host", "ck_ingest", "ck_phy_fam"],
                reset_port="host_rst_n", reset_pins=["host_rst_n", "rst_n"], regions=[dict(name="all", insts=["*"])])
    P = lp.Parent(spec)
    import fnmatch
    fam = {i: next(f for p, f in FAMILY.items() if fnmatch.fnmatchcase(i, p)) for i in P.region}
    reg = {i: ("core_hi" if i in hi else "core_lo") if fam[i] == "core" else fam[i] for i in P.region}
    drv, rd, _ = P.graph()
    g = collections.defaultdict(lambda: collections.Counter())
    for n, inst, pin in rd:
        for d in drv.get(n, ()):
            if not d.startswith("port:"):
                g[d][inst] += lp.eval_width(P.rng(n), P.env)
    cross, seen = [], set()
    for n, inst, pin in rd:
        for d in drv.get(n, ()):
            if d.startswith("port:") or (n, reg[inst]) in seen:
                continue
            rs, rr = reg[d], reg[inst]
            # same-family crossing: core_hi <-> core_lo, or a CDC leaf's core face <-> core_hi (cdc leaves sit in core_lo)
            if rs != rr and {rs, rr} <= {"core_hi", "core_lo", "cdc"} and "core_hi" in (rs, rr):
                seen.add((n, rr))
                cross.append(dict(net=n, src=d, dst=inst, src_region=rs, dst_region=rr,
                                  width=lp.eval_width(P.rng(n), P.env)))
    loops = sorted({tuple(sorted((h, l))) for h in P.region if reg[h] == "core_hi" for l in g[h]
                    if reg[l] != "core_hi" and reg[l] != "phy" and h in g[l]})
    bits = sum(c["width"] for c in cross)
    out = dict(hi=hi, regions=reg, crossing_nets=len(cross), crossing_bits=bits,
               ring_flops_est=bits * (P.D + 1), cross_region_2cycles=[list(x) for x in loops], crossings=cross)
    print(f"core split hi={hi}: {len(cross)} same-family crossing nets, {bits} b -> ~{bits * (P.D + 1)} ring flops "
          f"(D {P.D}, +{P.A} edges each); {len(loops)} cross-region 2-cycles (lp.py cannot keep the flat schedule):")
    for x in loops:
        print(f"  loop {x[0]} <-> {x[1]}  ({g[x[0]][x[1]]} b / {g[x[1]][x[0]]} b)")
    if a.json:
        Path(a.json).write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
