#!/usr/bin/env python3
"""KV-G3 10-24: plan v3.8v = v3.8u + FIRM sites for the hub_Ei fault-OR plan cells and internal stations on their two
long legs (R3-INTERNAL for plan cells).

Why (KV-G3 hub_Ei G3 4_cts, 10-24): kv3_hub_Ei.contents hp_fault_1052/1087/1132/1182 (qkd_hp_or2, one flop each) had
no origin_um, so G0's R3-INTERNAL check never saw them and GPL put them anywhere.  hp_fault_1052 = OR(i_dcal_flt
(N face, x 1004), i_ahub_hf (W face, y 20)) feeding a chain that ends at o_hp_fault_N_q (W face, y 458): the
dcal leg was 2.2 mm with no register -> TT setup -679 ps; hp_fault_1087 takes i_hp_fault_N_q from the E face
(y 184): 1.5 mm -> TT -250 ps.  Fix (no window move: L357 arrives from the E corridor, L758 from hub_Eo):
  * the four OR cells sit FIRM in a W-face cluster beside the chain's other windows (y 432..459);
  * bus:i_dcal_flt gets 3 FIRM stations on the L path (1004,1676) -> (1004,432) -> (17,432), hops 558 um;
  * bus:i_hp_fault_N_q gets 2 FIRM stations on (1279,184) -> (17,184) -> (17,441), hops 506 um;
  * lanes L357 (dcal.flt) fixed_cycles += 3, L758 (hp_fault_3.q) fixed_cycles += 2 (gen.py latency recomputes).
Fault-path cost: +3 / +2 cycles of fault age on those two inputs of the hub_C/hub_Wi fault tree (u_efault AGE must
cover it: bind check).  Touches only partition_types.kv3_hub_Ei.{contents origin/outline, internal_stations} and
lanes L357 / L758.   usage: post_v38v.py die_plan.json > die_plan.json"""
import json
import sys

HOP = 675.0
CELL = 4.32
SITES = {"hp_fault_1052": [17.28, 432.0], "hp_fault_1087": [17.28, 440.64], "hp_fault_1132": [17.28, 449.28],
         "hp_fault_1182": [17.28, 457.92]}


def stations(pts, n):
    """n equally spaced points along the Manhattan polyline pts (excluding both ends), and the hop length"""
    L = sum(abs(a[0] - b[0]) + abs(a[1] - b[1]) for a, b in zip(pts, pts[1:]))
    h = L / (n + 1)
    out = []
    for j in range(1, n + 1):
        t = h * j
        for a, b in zip(pts, pts[1:]):
            d = abs(a[0] - b[0]) + abs(a[1] - b[1])
            if t <= d:
                f = t / d if d else 0.0
                out.append([round(a[0] + f * (b[0] - a[0]), 3), round(a[1] + f * (b[1] - a[1]), 3)])
                break
            t -= d
    return out, L, h


def main():
    p = json.load(open(sys.argv[1]))
    t = p["partition_types"]["kv3_hub_Ei"]
    for c in t["contents"]:
        if c["inst"] in SITES:
            c["origin_um"] = SITES[c["inst"]]
            c["outline_um"] = [CELL, CELL]
            c["note"] = c.get("note", "") + " | v3.8v FIRM site (KV-G3 R3-INTERNAL plan cell)"
    legs = [("bus:i_dcal_flt", "L357", [[1004.088, 1676.064], [1004.088, 432.0], [21.6, 432.0]], 3,
             "face:N", "hp_fault_1052.a"),
            ("bus:i_hp_fault_N_q", "L758", [[1278.624, 184.152], [21.6, 184.152], [21.6, 440.64]], 2,
             "face:E", "hp_fault_1087.b")]
    ist = [e for e in t.get("internal_stations", []) if e.get("conn") not in {g[0] for g in legs}]
    for conn, lane, pts, n, launch, cap in legs:
        regs, L, h = stations(pts, n)
        assert h <= HOP, (conn, h)
        ist.append(dict(conn=conn, from_um=pts[0], to_um=pts[-1], regs_um=regs, bits=1, launch=launch, capture=cap,
                        note=f"KV-G3 v3.8v R3-INTERNAL FIRM (plan cell): path {L:.0f} um, {n} stations, hop {h:.0f} <= {HOP:g}"))
        ln = next(x for x in p["lanes"] if x["id"] == lane)
        ln["fixed_cycles"] = ln.get("fixed_cycles", 0) + n
        ln["note"] = ln.get("note", "") + f" | +{n} FIRM hub_Ei internal stations (KV-G3 v3.8v, plan-cell R3-INTERNAL)"
    t["internal_stations"] = ist
    p["note"] = p.get("note", "") + " | v3.8v (KV-G3 10-24): hub_Ei fault-OR cells FIRM + internal stations L357 +3, L758 +2"
    json.dump(p, sys.stdout, indent=1)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
