#!/usr/bin/env python3
"""DIE-S81-36 (post-freeze one-block fixes, COORD 12:5x): two plan-data fixes queued by the S81 kit wave.

(1) phy__t1 (S81-KITS-H 12:04 (2)): content u_phy_hbm carried no view/site, so the kit had no PHY macro.  The bound
    partition RTL (bind.py kit-rtl) instantiates the K-only macro ot_hbm3e_phy_v41x_aw30_e8p5_k as u_core
    (kit path u_bound.u_core; d4a7aeda9).  The content keeps its logical bind identity (inst u_phy_hbm, module
    ot_hbm3e_phy_v41x_aw30_e8p5) and gets physical_inst/physical_master (gen_phys content_physical_identity), the
    v2 _k LEF + TT lib, outline 8500.056 x 1177.2 and a site at the S (die-edge, bump-field) side of the 8657.28 x
    1226.88 slot: x centred and snapped down to the 8.64 lattice (77.76), y 0, R0 -- all 19907 signal pins of the
    macro are on its N edge (M5), facing the slot's N-face buses.  core_pg_connect: true (no die PHY PG domain covers phy_hbm, so the
    macro's own VDD/VSS M4 pins land on the core grid; G0C core_pg rule).  Outline, buses, pins, neighbours unchanged.
(2) seqhost__t1: not a plan-data fix (lane unit__seqhost__gunit is 267 on 14 types; ASK to COORD).
Every other byte of the plan JSON is asserted unchanged.
usage (repo root): delta_phy_seq_1030.py PLAN_IN PLAN_OUT"""
import copy
import json
import re
import sys

LAT = 8.64
VIEW = "physical/asap7_memory_macros_v2/ot_hbm3e_phy_v41x_aw30_e8p5_k/ot_hbm3e_phy_v41x_aw30_e8p5_k"
SIZE = [8500.056, 1177.2]


def lef_size(path):
    m = re.search(r"SIZE\s+([\d.]+)\s+BY\s+([\d.]+)", open(path).read())
    return [float(m.group(1)), float(m.group(2))]


def splice(text, name, obj):
    m = re.search(r'^  "' + re.escape(name) + r'": ', text, re.M)
    assert m, name
    i = m.end()
    _, j = json.JSONDecoder().raw_decode(text, i)
    return text[:i] + json.dumps(obj, indent=1).replace("\n", "\n  ") + text[j:]


def main():
    src, dst = sys.argv[1], sys.argv[2]
    text = open(src).read()
    plan = json.loads(text)
    exp = copy.deepcopy(plan)
    t = exp["partition_types"]["phy__t1"]
    assert lef_size(VIEW + ".lef") == SIZE
    (c,) = [c for c in t["contents"] if c["inst"] == "u_phy_hbm"]
    assert "lef" not in c and "origin_um" not in c
    W, H = t["outline_um"]
    x = int(round((W - SIZE[0]) / 2 / LAT, 6)) * LAT
    assert 0 <= x and x + SIZE[0] <= W and SIZE[1] <= H
    c.update(physical_inst="u_bound.u_core", physical_master="ot_hbm3e_phy_v41x_aw30_e8p5_k",
             lef=VIEW + ".lef", lib=VIEW + "_tt.lib", origin_um=[round(x, 4), 0.0], outline_um=SIZE, orient="R0",
             obs_max="M5")
    c["note"] += ("; DIE-S81-36 10-30: view = K-only macro ot_hbm3e_phy_v41x_aw30_e8p5_k (the bound RTL's u_core), "
                  "site at the S die-edge side, signal pins N/M5")
    assert "core_pg_connect" not in t
    t["core_pg_connect"] = True     # no PHY PG domain covers phy_hbm: the macro's VDD/VSS (M4) land on the tile grid
    text = splice(text, "phy__t1", t)
    out = json.loads(text)
    assert out == exp
    open(dst, "w").write(text)
    print(json.dumps(c, indent=1))


if __name__ == "__main__":
    main()
