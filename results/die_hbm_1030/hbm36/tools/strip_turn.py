#!/usr/bin/env python3
"""DIE-HBM-36 V-A turn capacity: per strip partition, N-S wire capacity on every horizontal cut (250-um step) inside
the strip, exactly as check.check_cuts computes a partition segment (cores = declared/routed union, ft_track_frac share,
die_ft_bands share), and the same with the whole strip width declared as one NS die_ft_band (share 1.0) = the most a
V-A band declaration could give.  bits = plan lane segments crossing the cut inside the strip.  limit 0.6.
usage: strip_turn.py WT PLANDIR OUT_JSON"""
import sys, json
sys.path.insert(0, sys.argv[1] + "/tools/die_plan")
import schema as S, check as C
from die_trial import die_core_rects, ft_band_rects
P = S.Plan(json.load(open(sys.argv[2] + "/die_plan.json")), None)
geo = {lid: C.lane_geometry(P, lid) for lid in P.lanes}
segs = []
for lid, (pts, _, _) in geo.items():
    w = P.ports[P.lanes[lid]["ports"][0]]["width"]
    segs += [(p, q, w) for p, q in zip(pts, pts[1:])]
cores = {L: die_core_rects(P, L) for L in ("M5", "M7")}
bands = ft_band_rects(P)
lim = P.budgets["cut_ratio_max"]
out = {}
for half in ("NE", "NW"):
    for s in ("b000", "b010", "b001", "b011", "b002", "b012", "b003", "b013"):
        pn = f"{half}_{s}"; r = P.rect(pn); x0, y0, x1, y1 = r
        frac = P.ptype(pn).get("ft_track_frac", C.FT_TRACK_FRAC)
        rows = []
        c = (int(y0 // 250) + 1) * 250
        while c < y1 - 1:
            bits = sum(w for p, q, w in segs if min(p[1], q[1]) < c - 1e-6 and max(p[1], q[1]) > c + 1e-6 and x0 - 1e-6 <= p[0] <= x1 + 1e-6)
            cap = capmax = 0.0
            for L in ("M5", "M7"):
                obs = [(cr[0], cr[2]) for cr in cores[L] if cr[1] + 1e-6 < c < cr[3] - 1e-6]
                res = [(br[1], br[3], br[5]) for br in bands if br[0] == L and br[2] + 1e-6 < c < br[4] - 1e-6]
                pitch = P.layers[L]["pitch_um"]
                cap += C.cut_interval_tracks(x0, x1, pitch, frac, obs, res)
                capmax += C.cut_interval_tracks(x0, x1, pitch, frac, obs, [(x0, x1, 1.0)])
            rows.append(dict(y=c, bits=bits, cap=round(cap), ratio=round(bits / cap, 3) if cap else None,
                             spare06=int(lim * cap - bits), capmax=round(capmax), spare06_max=int(lim * capmax - bits)))
            c += 250
        out[pn] = dict(width=round(x1 - x0, 2), frac=frac, rows=rows,
                       min_spare06=min(r_["spare06"] for r_ in rows), min_spare06_max=min(r_["spare06_max"] for r_ in rows))
json.dump(out, open(sys.argv[3], "w"), indent=1)
tot = tm = 0
for pn, d in out.items():
    if pn.startswith("NE"):
        tot += d["min_spare06"]; tm += d["min_spare06_max"]
    print(pn, d["width"], "frac", d["frac"], "min spare@0.6 now", d["min_spare06"], "| whole-width band", d["min_spare06_max"],
          "| worst row", max(d["rows"], key=lambda r_: r_["ratio"] or 0))
print("NE sum of per-strip min spare: now", tot, "whole-width bands", tm)
