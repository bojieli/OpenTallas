#!/usr/bin/env python3
"""stage_s81_tapwin_floor.py: S81 ready12b TAPWIN-FLOOR stage (GEN-CLASS-1 11-12, COORD; DIE-S81-88).

    stage_s81_tapwin_floor.py PLAN OUT --kitwin KITWIN.json [--phy-type phy__t1] [--phy-cap 20]

GEN-CLASS-1 found 36 of 18,484 S81 per-port kit windows under 10 ps (13 slice_station types) and
phy__t1 with per_type_ps = 0 and no per_port table, so HEAD-95's floor (tap_window_floor.py) could not act on it.

Stage (one plan edit, then the main-line floor rule unchanged):
  1. phy type: per_type_ps[phy] = max(old, --phy-cap) (cap, = ceil10(need + 10) + 10 as in DIE-S81-41's rule; need 0),
     and per_port_ps[phy] = the type's measured per-port needs from KITWIN (die_sta_related --kit-window-out),
     so the floor can raise them; a per_port table that already exists is kept.
  2. tap_window_floor.floor_windows(plan, floor 10, margin 10) on every type, WITHOUT per-port needs by default:
     KITWIN here is the r7b proof on an older clock (plan 4cf8fb2f1479), so need + margin would re-derive 505 ports on
     42 types; that re-derivation waits for the ready12b clock of record (--floor-needs turns it on).
Windows are only raised; every change is printed; each changed type's kit SDC changes and needs a re-sign.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tap_window_floor as TWF  # noqa: E402


def stage(plan, kitwin, phy="phy__t1", phy_cap=20.0, floor=10.0, margin=10.0, floor_needs=False):
    tw = plan["clock"]["tap_window"]
    pt = tw.setdefault("per_type_ps", {})
    pp = tw.setdefault("per_port_ps", {})
    pre = []
    if phy in pt or phy in (kitwin.get("per_port_ps") or {}):
        old = float(pt.get(phy, tw.get("window_ps", 0.0)))
        if phy_cap > old:
            pt[phy] = phy_cap
            pre.append((phy, "per_type", old, phy_cap))
        if not pp.get(phy):
            need = (kitwin.get("per_port_ps") or {}).get(phy)
            if not need:
                raise SystemExit("TAPWIN-FLOOR: no measured per-port need for %s in KITWIN" % phy)
            pp[phy] = {p: float(v) for p, v in sorted(need.items())}
            pre.append((phy, "per_port", None, dict(pp[phy])))
    ch = TWF.floor_windows(plan, kitwin if floor_needs else None, floor, margin)
    if pre:
        tw["per_port_note"] = (tw.get("per_port_note", "") + " | TAPWIN-FLOOR-S81 (GEN-CLASS-1, COORD 11-12): %s per_type "
                               "raised to %g and per_port taken from the measured need so the floor acts" % (phy, phy_cap)).strip(" |")
    return pre, ch


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plan")
    ap.add_argument("out")
    ap.add_argument("--kitwin", required=True)
    ap.add_argument("--phy-type", default="phy__t1")
    ap.add_argument("--phy-cap", type=float, default=20.0)
    ap.add_argument("--floor-needs", action="store_true", help="also apply need + margin from KITWIN")
    a = ap.parse_args(argv)
    plan = json.load(open(a.plan))
    kw = json.load(open(a.kitwin))
    pre, ch = stage(plan, kw, a.phy_type, a.phy_cap, floor_needs=a.floor_needs)
    with open(a.out, "w") as f:
        json.dump(plan, f, indent=1)
        f.write("\n")
    for c in pre:
        print("PRE %s.%s %s -> %s" % c)
    for c in ch:
        print("W %s.%s %g -> %g" % c)
    print("changed ports", len(ch), "types", len({c[0] for c in ch}), sorted({c[0] for c in ch}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
