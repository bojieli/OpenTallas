#!/usr/bin/env python3
"""CUT-SEGMENTS-1 (S81-DIE-R3 11-17, COORD): census of every partition / channel cut segment over budgets.cut_ratio_max.

G0 (check.check_cuts) raises one ERROR per cut line (its worst segment); the other segments over the limit on that line
are WARN cuts_segments.  This prints and writes the full set from the same model: per over-limit segment its bits,
tracks, the bits it must shed (need_bits), its crossing lanes (most bits first) and every segment of the same cut line
with its slack at the limit (where the bits could go).

usage: cut_census.py PLAN.json [--out census.json] [--lanes N]
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check as CK  # noqa: E402
import schema as S  # noqa: E402


def census(raw):
    P = S.Plan(raw)
    R = CK.Report()
    geo = {lid: CK.lane_geometry(P, lid) for lid in P.lanes}
    out = CK.check_cuts(P, R, geo)
    return out["over_segments"], P.budgets["cut_ratio_max"]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("plan")
    ap.add_argument("--out")
    ap.add_argument("--lanes", type=int, default=8, help="lanes printed per segment")
    a = ap.parse_args(argv)
    segs, lim = census(json.load(open(a.plan)))
    if a.out:
        with open(a.out, "w") as f:
            json.dump({"cut_ratio_max": lim, "over_segments": segs}, f, indent=1)
    for s in segs:
        print(f"CUT {s['orient']}@{s['at_um']:g} {s['part']} {s['ratio']:.3f} bits {s['bits']} tracks {s['tracks']} "
              f"need {s['need_bits']}{' WORST' if s['worst_of_cut'] else ''} lanes "
              + ", ".join(f"{l}:{b}" for l, b in s["lanes"][:a.lanes]))
    print(f"CUT-SEGMENTS {len(segs)} over {lim} on {len({(s['orient'], s['at_um']) for s in segs})} cut lines")
    return 0


if __name__ == "__main__":
    sys.exit(main())
