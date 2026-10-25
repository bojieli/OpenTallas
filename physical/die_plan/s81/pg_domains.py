#!/usr/bin/env python3
"""S81 OWNER DECISION 7 (2026-10-24, IR over SerDes windows): one separate PHY supply per SerDes window.

usage: pg_domains.py PLAN.json DIE_IO.json [--split]
Writes die.io (the die_io.py windows) and die.pg.domains into PLAN.json in place, in the same form as HBM B2m
(physical/die_plan/hbm_arch/b2m.py pg_domains) and the S81 head plan: own net VDDPHY with VSS, dense M8/M9 straps over
the window plus a one-bump guard ring, dedicated power/ground C4 rows (45-um array) over the PHY macro.  The partition
strip with boundary flops and ft stations stays on core VDD.  Checked by check.py rule pg_domain.
Basis: TRIAL-S81 10-24 IR: SerDes windows 235/270 mV FAIL on the shared grid.
"""
import copy
import json
import sys

PHY_GRID = [dict(layer="M8", width_um=1.92, pitch_um=8.64, offset_um=4.32, nets=["VDDPHY", "VSS"]),
            dict(layer="M9", width_um=1.92, pitch_um=8.64, offset_um=4.32, nets=["VDDPHY", "VSS"])]
PHY_BUMP_PITCH = 45.0
PHY_GUARD_UM = 63.64
# --split (S81.IR candidate, 2026-10-24): the PHY macro at a published 7-nm 112G LR area (0.35-0.5 mm2/lane ->
# 0.40 x 6 lanes = 2.4 mm2, the HBM B2m IR README figure) on the die-edge side of the window, inset by the guard on
# its E/W/inner sides; the domain = macro + guard INSIDE the serdes partition (never in a neighbour); the rest of the
# window (inner face) is the core strip for boundary flops / ft stations on core VDD with core C4.  Basis: S81.IR
# window PDNSim (results/die_trial_1024/s81_ir_vddphy): the unsplit domain covers the whole partition + 63.64 um of
# each neighbour, so the strip logic and the neighbours' guard band have no core M8/M9 VDD.
# core_edge_bumps "relocate": a 150-um core lattice C4 that falls inside the domain rect within half a pitch of an
# edge facing core moves 15 um outside that edge (S81.IR: without it the WS3 domain's W edge loses a core bump
# column and the fW0 cells there see 38.8 mV VDD / 39.7 mV VSS).
PHY_AREA_MM2 = 2.4
GRID = 8.64


def split_domain(w, W, H):
    x0, y0, x1, y1 = w["rect_um"]
    g = PHY_GUARD_UM
    south = (y0 + y1) / 2 < H / 2
    mx0, mx1 = x0 + g, x1 - g
    h = -(-PHY_AREA_MM2 * 1e6 / (mx1 - mx0) // GRID) * GRID
    assert h + g < (y1 - y0), (w["name"], h)
    if south:
        mac = [round(mx0, 4), y0, round(mx1, 4), round(y0 + h, 4)]
        dom = [x0, round(max(0.0, y0 - g), 4), x1, round(y0 + h + g, 4)]
        strip = [x0, dom[3], x1, y1]
    else:
        mac = [round(mx0, 4), round(y1 - h, 4), round(mx1, 4), y1]
        dom = [x0, round(y1 - h - g, 4), x1, round(min(H, y1 + g), 4)]
        strip = [x0, y0, x1, dom[1]]
    return mac, dom, strip


def domains(io, W, H, split=False):
    out = []
    for w in io:
        if w.get("iface") != "serdes":
            continue
        x0, y0, x1, y1 = w["rect_um"]
        g = PHY_GUARD_UM
        out.append(dict(
            name=f"phy_{w['part']}", nets=["VDDPHY", "VSS"], io=[w["name"]],
            rect_um=[round(max(0.0, x0 - g), 4), round(max(0.0, y0 - g), 4), round(min(W, x1 + g), 4),
                     round(min(H, y1 + g), 4)],
            grid=copy.deepcopy(PHY_GRID),
            bumps=dict(rect_um=[x0, y0, x1, y1], pitch_um=PHY_BUMP_PITCH, use="power_ground",
                       note="dedicated VDDPHY/VSS C4 rows over the SerDes macro (45-um array); no signal bumps inside "
                            "except the window's own SerDes sites"),
            note="OWNER decision 7 (10-24): separate PHY supply + dedicated bump rows over the SerDes window; core VDD "
                 "grid (partition strip, boundary flops, ft stations) unchanged around it; basis TRIAL-S81 10-24 IR "
                 "235/270 mV FAIL on the shared grid"))
        if split:
            mac, dom, strip = split_domain(w, W, H)
            out[-1].update(rect_um=dom, phy_macro_um=mac, core_strip_um=strip, core_edge_bumps="relocate")
            out[-1]["bumps"]["rect_um"] = mac
            out[-1]["note"] += ("; SPLIT candidate (S81.IR): PHY macro %.1f mm2 at the die edge, domain = macro + guard "
                                "inside the partition, inner strip on core VDD + core C4 (ft slots / boundary flops "
                                "must sit in core_strip_um)" % PHY_AREA_MM2)
    return out


def main():
    pf, iof = sys.argv[1], sys.argv[2]
    split = "--split" in sys.argv[3:]
    plan = json.load(open(pf))
    io = json.load(open(iof))
    W, H = plan["die"]["outline_um"]
    plan["die"]["io"] = io
    plan["die"]["pg"]["domains"] = domains(io, W, H, split)
    with open(pf, "w") as f:
        json.dump(plan, f, indent=1)
        f.write("\n")
    print(f"pg_domains: {len(plan['die']['pg']['domains'])} VDDPHY domains over {len(io)} die.io windows")


if __name__ == "__main__":
    main()
