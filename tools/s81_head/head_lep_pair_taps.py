#!/usr/bin/env python3
"""DIE-HEAD-10 LEP-C0: move hd_lep0N reset.local_taps_um that the applied PAIR children / parent SRAM block to the nearest free 4.32-um site; report the worst free-point Manhattan reach (relay reach 405 um).  Run from the repo root: python3 tools/s81_head/head_lep_pair_taps.py PLAN.json (in place)"""
import json, sys, math
sys.path.insert(0, "tools/die_plan")
import reset_tree as R
import numpy as np
p = sys.argv[1]; P0 = json.load(open(p))
t = P0["partition_types"]["hd_lep0N"]; w, h = t["outline_um"]
boxes = R.blockages(t); C = R.CLEAR_UM; area = (C, C, w - C, h - C)
taps = [list(map(float, xy)) for xy in t["reset"]["local_taps_um"]]
moved = []
for i, (x, y) in enumerate(taps):
    if R._free((x, y), boxes, area): continue
    best = None
    for gx in np.arange(C, w - C, 4.32):
        for gy in np.arange(C, h - C, 4.32):
            gx2, gy2 = round(float(gx) / 4.32) * 4.32, round(float(gy) / 4.32) * 4.32
            if not R._free((gx2, gy2), boxes, area): continue
            d = abs(gx2 - x) + abs(gy2 - y)
            if best is None or d < best[0]: best = (d, gx2, gy2)
    moved.append(((x, y), (round(best[1], 2), round(best[2], 2)), round(best[0], 2)))
    taps[i] = [round(best[1], 2), round(best[2], 2)]
t["reset"]["local_taps_um"] = taps
# worst Manhattan reach from any free point to its nearest tap (incl. clock taps)
allt = [(a, b) for _, a, b in R._taps(type("P", (), {})(), "x")] if False else []
pts = [(gx, gy) for gx in np.arange(C, w - C, 8.64) for gy in np.arange(C, h - C, 8.64) if R._free((gx, gy), boxes, area)]
T = np.array(taps); worst = max(float(np.min(np.abs(T[:, 0] - x) + np.abs(T[:, 1] - y))) for x, y in pts)
json.dump(P0, open(p, "w"), indent=2); open(p, "a").write("\n")
print(json.dumps(dict(moved=moved, local_taps=len(taps), free_pts=len(pts), worst_local_reach_manhattan_um=round(worst, 1))))
