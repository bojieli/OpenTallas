#!/usr/bin/env python3
"""S81 OWNER DECISION 7 (2026-10-24, IR over SerDes windows): one separate PHY supply per SerDes window.

usage: pg_domains.py PLAN.json DIE_IO.json
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


def domains(io, W, H):
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
    return out


def main():
    pf, iof = sys.argv[1], sys.argv[2]
    plan = json.load(open(pf))
    io = json.load(open(iof))
    W, H = plan["die"]["outline_um"]
    plan["die"]["io"] = io
    plan["die"]["pg"]["domains"] = domains(io, W, H)
    with open(pf, "w") as f:
        json.dump(plan, f, indent=1)
        f.write("\n")
    print(f"pg_domains: {len(plan['die']['pg']['domains'])} VDDPHY domains over {len(io)} die.io windows")


if __name__ == "__main__":
    main()
