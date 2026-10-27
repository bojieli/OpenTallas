#!/usr/bin/env python3
"""PATH-S81-PD6 cut evidence step 2: routed demand per strip gcell from the PD5 GRT guides (route_<C>.guide).

dbGCellGrid usage (probe) = adjustment-reserved tracks + obstruction-blocked tracks + routed demand, so it cannot give
the routed share alone.  Here, per strip gcell and layer:
  d_all   = number of nets whose guide box on that layer covers the gcell (GRT 3D usage proxy, includes via/turn gcells)
  d_cross = nets whose box on that layer spans ACROSS the cut line (extent on both sides of it) = wires crossing the cut
Effective routing capacity reconstructed as cap_eff = cap - usage + d_all (cap and usage from dbGCellGrid).
Also writes whole-die per-layer guide gcell sums (sanity vs the GRT log's per-layer demand)."""
import json
import sys
from collections import defaultdict

corner = sys.argv[1]
guide = sys.argv[2]
G = 10800                                  # gcell pitch dbu (OT_GRID x1/y1), dbu 1000/um
strip = defaultdict(dict)                  # (o,at) -> {(L,xi,yi): [cap,use]}
for ln in open(f"probe_{corner}/gcells_{corner}.txt"):
    o, at, L, xi, yi, x0, y0, cap, use = ln.split()
    strip[(o, float(at))][(L, int(xi), int(yi))] = [float(cap), float(use)]
cuts = json.load(open("cuts_composed.json"))
idx = defaultdict(list)                    # L -> [(o, c_dbu, key, ranges)]
for c in cuts:
    k = (c["orient"], c["at_um"])
    keys = strip[k]
    xs = sorted({xi for (_, xi, _) in keys})
    ys = sorted({yi for (_, _, yi) in keys})
    for L in ("M4", "M5", "M6", "M7", "M8", "M9"):
        idx[L].append((c["orient"], round(c["at_um"] * 1000), k, xs[0], xs[-1], ys[0], ys[-1]))
d_all = defaultdict(int)
d_cross = defaultdict(int)
gsum = defaultdict(int)
for ln in open(guide):
    p = ln.split()
    if len(p) != 5:
        continue
    L = p[4]
    if L not in idx:
        continue
    x0, y0, x1, y1 = map(int, p[:4])
    gx0, gx1 = x0 // G, (x1 - 1) // G
    gy0, gy1 = y0 // G, (y1 - 1) // G
    gsum[L] += (gx1 - gx0 + 1) * (gy1 - gy0 + 1)
    for o, c, k, xa, xb, ya, yb in idx[L]:
        if gx1 < xa or gx0 > xb or gy1 < ya or gy0 > yb:
            continue
        crosses = (y0 < c < y1 and gy1 > gy0) if o == "horizontal" else (x0 < c < x1 and gx1 > gx0)
        for xi in range(max(gx0, xa), min(gx1, xb) + 1):
            for yi in range(max(gy0, ya), min(gy1, yb) + 1):
                kk = (L, xi, yi)
                if kk in strip[k]:
                    d_all[(k, kk)] += 1
                    if crosses:
                        d_cross[(k, kk)] += 1
out = []
for k, cells in strip.items():
    for kk, (cap, use) in cells.items():
        da, dc = d_all.get((k, kk), 0), d_cross.get((k, kk), 0)
        out.append(dict(orient=k[0], at=k[1], L=kk[0], xi=kk[1], yi=kk[2], cap=cap, use=use, d_all=da, d_cross=dc,
                        cap_eff=cap - use + da))
json.dump(dict(doc=__doc__, gcells=out, guide_gcell_sum=gsum), open(f"strip_demand_{corner}.json", "w"))
print("guide gcell sums", dict(gsum))
neg = sum(1 for r in out if r["cap_eff"] < r["d_all"] - 1e-9)
print("strip gcells", len(out), "cap_eff<d_all", neg, "use<d_all (inconsistent)", sum(1 for r in out if r["use"] < r["d_all"]))
