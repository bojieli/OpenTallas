#!/usr/bin/env python3
"""DIE-HBM-57 variant D: +1 station on slots whose entry/inner die hop > 405 cannot be fixed by siting (hop-sum/k > ~395).
mk_d.py BASE OUT TYPE:SLOT ... ; regs on the slot's existing row, x grid-searched (first x, pitch) to min the max die hop of the lane.
Then run gen.py latency --inplace on OUT."""
import json, sys, itertools
sys.path.insert(0, "/srv/opentallas-scratch2/claude/wt/die-hbm-56/tools/die_plan")
import numpy as np, schema as S, check as C
base, out = sys.argv[1:3]; tg = [a.split(":", 2) for a in sys.argv[3:]]
d = json.load(open(base))
def lanes_of(P, t, sl):
    return [lid for lid in P.lanes for x in P.lane_crossings(lid) if P.parts[x[0]]["type"] == t and x[1] == sl]
for row in tg:
    t, sl = row[:2]; anchors = [[float(v) for v in q.split(",")] for q in row[2].split(";")] if len(row) > 2 else None
    s = next(x for x in d["partition_types"][t]["ft_slots"] if x["name"] == sl)
    for k in ("bit_sites_um", "bit_site_cell_um"): s.pop(k, None)
    k = int(s["stations"]) + 1; s["stations"] = k
    r = np.array(anchors if anchors else s["regs_um"], float)
    e0 = r[0] + (r[0] - r[1]) / np.abs(r[0] - r[1]).sum() * 400; e1 = r[-1] + (r[-1] - r[-2]) / np.abs(r[-1] - r[-2]).sum() * 400
    poly = np.vstack([e0, r, e1]); seg = np.abs(np.diff(poly, axis=0)).sum(axis=1); cum = np.concatenate([[0], np.cumsum(seg)])
    def at(u):
        i = min(np.searchsorted(cum, u, side="right") - 1, len(seg) - 1); f = (u - cum[i]) / seg[i]; return poly[i] + f * (poly[i + 1] - poly[i])
    ow, oh = d["partition_types"][t]["outline_um"]
    P = S.Plan(d, None); L = lanes_of(P, t, sl)
    boxes = list(S.placed_macro_boxes(d["partition_types"][t]).values())
    best = None
    for u0 in np.arange(100, 800, 10):
        for pitch in np.arange(150, 400, 5):
            us = u0 + pitch * np.arange(k)
            if us[-1] > cum[-1]: continue
            pts = [at(u) for u in us]
            if any(p[0] < 2 or p[1] < 2 or p[0] > ow - 2 or p[1] > oh - 2 for p in pts): continue
            if any(x0 - 1.5 < p[0] < x1 + 1.5 and y0 - 1.5 < p[1] < y1 + 1.5 for p in pts for (x0, y0, x1, y1) in boxes): continue
            s["regs_um"] = [[round(float(p[0]), 3), round(float(p[1]), 3)] for p in pts]
            hs = []
            for lid in L:
                _, regs, _ = C.lane_geometry(P, lid); hs += list(C.lane_pin_hops(P, lid, regs))
            m = tuple(sorted((round(h, 1) for h in hs), reverse=True)[:6])
            if best is None or m < best[0]: best = (m, s["regs_um"])
    s["regs_um"] = best[1]; print(t, sl, "stations", k, "lanes", L, "max die hop", best[0][:3], flush=True)
json.dump(d, open(out, "w"))
