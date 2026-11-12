#!/usr/bin/env python3
"""Split heavy clock taps from a PLACED sink inventory (X-TIER-OTC 11-12, COORD GEOM "tap loading very uneven").

A grid+explicit type's kit splits its real registers to the NEAREST tap (clock_taps.tcl) and caps a tap at
OT_TAP_MAX_SINKS (= clock.tap_max_sinks, else 3000).  The plan model only sees planned sinks, so dense soft regions
(leaf datapath, form-(d) bays) put 1600-2200 real sinks on one tap (S81 t8 clk_t28 2217) while edge taps hold single
digits.  This pass reads the placed sinks of the clock port (tap_sinks_dump.tcl, pre-CTS DB), runs the kit's nearest
split on the plan's tap set, and splits every tap above --target into ceil(load / target) taps at the k-medians of its
own sinks (each moved to the nearest legal tap site: outline / hard-core halo / tap spacing as bay_taps).  Existing
tap names are kept (new taps are appended to clock.added_taps).  It then sets clock.tap_max_sinks = --cap, so the
kit's cap pass moves any remaining excess to a neighbour tap instead of letting one tap grow.

  python3 tap_split.py PLAN_IN PLAN_OUT --sinks TYPE=placed_sinks.json [...] [--target 700] [--cap 800]
"""
import argparse, json, math, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import schema as S                     # noqa: E402
import taps                            # noqa: E402
import bay_taps as BT                  # noqa: E402
from placement_obstacles import placement_boxes   # noqa: E402

SEARCH_UM = 43.2      # a split tap sits within this box half-size of its sinks' median


def nearest(sites, sinks):
    """kit split (clock_taps.tcl / taps.assign step 1): sink -> nearest tap (Manhattan, ties to the lower index)."""
    load = [0] * len(sites)
    asg = []
    for x, y in sinks:
        j = min(range(len(sites)), key=lambda k: (abs(x - sites[k][1]) + abs(y - sites[k][2]), k))
        asg.append(j)
        load[j] += 1
    return load, asg


def split_type(raw, tn, sinks, target, cap, rounds=6):
    t = raw["partition_types"][tn]
    ck = t["clock"]
    if ck.get("tap_mode") != "grid+explicit":
        return dict(skipped=f"tap_mode {ck.get('tap_mode')}")
    w, h = t["outline_um"]
    boxes = list(placement_boxes(t, halo=S.TAP_CLEAR_UM).values())
    table = ck.setdefault("added_taps", [])
    P = BT._plan(raw)
    n_grid = len(S._grid_taps(P, tn))
    sites0 = taps.grid_explicit_sites(P, tn)
    load0, _ = nearest(sites0, sinks)
    added, unsited = 0, 0
    for _ in range(rounds):
        P = BT._plan(raw)
        sites = taps.grid_explicit_sites(P, tn)
        load, asg = nearest(sites, sinks)
        heavy = [j for j in range(len(sites)) if load[j] > target]
        if not heavy:
            break
        taken = [(x, y) for _, x, y in sites]
        new = []
        for j in sorted(heavy, key=lambda j: -load[j]):
            pts = [s for s, a in zip(sinks, asg) if a == j]
            k = math.ceil(load[j] / target)
            cen, groups = taps._kmedians(pts, k)
            # the group nearest the existing tap keeps it; every other group gets a new tap at its median
            keep = min(range(len(cen)), key=lambda c: abs(cen[c][0] - sites[j][1]) + abs(cen[c][1] - sites[j][2]))
            for c, (cx, cy) in enumerate(cen):
                if c == keep or not groups[c]:
                    continue
                xy = None
                for r in (SEARCH_UM, 2 * SEARCH_UM, 3 * SEARCH_UM):     # widen only when the median sits in a halo
                    box = [max(0.0, cx - r), max(0.0, cy - r), min(w, cx + r), min(h, cy + r)]
                    xy = BT.site(box, w, h, S.TAP_CLEAR_UM, taken, boxes)
                    if xy is not None:
                        break
                if xy is None:
                    unsited += 1
                    continue
                taken.append(xy)
                new.append(xy)
        if not new:
            break
        for xy in new:
            table.append({"name": f"clk_t{n_grid + len(table)}", "xy": [xy[0], xy[1]]})
        added += len(new)
    P = BT._plan(raw)
    sites = taps.grid_explicit_sites(P, tn)
    load, _ = nearest(sites, sinks)
    if int(ck.get("tap_max_sinks", 10 ** 9)) > cap:
        ck["tap_max_sinks"] = cap
    return dict(sinks=len(sinks), taps_before=len(sites0), taps_after=len(sites), added=added, unsited=unsited,
                max_before=max(load0), max_after=max(load), over_target_after=sum(1 for v in load if v > target),
                over_cap_after=sum(1 for v in load if v > cap), excess_over_cap=sum(max(0, v - cap) for v in load),
                tap_max_sinks=ck["tap_max_sinks"])


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("plan")
    ap.add_argument("out")
    ap.add_argument("--sinks", action="append", default=[], help="TYPE=placed sinks JSON [[x, y], ...]")
    ap.add_argument("--target", type=int, default=700)
    ap.add_argument("--cap", type=int, default=800)
    a = ap.parse_args(argv)
    BT.PLAN_PATH = str(Path(a.plan).resolve())
    raw = json.load(open(a.plan))
    rc = 0
    for spec in a.sinks:
        tn, f = spec.split("=", 1)
        if tn not in raw["partition_types"]:
            print("TAP_SPLIT", tn, "absent"); rc = 1; continue
        sinks = [(float(p[0]), float(p[1])) for p in json.load(open(f))]
        r = split_type(raw, tn, sinks, a.target, a.cap)
        print("TAP_SPLIT", tn, json.dumps(r))
    json.dump(raw, open(a.out, "w"))
    return rc


if __name__ == "__main__":
    sys.exit(main())
