#!/usr/bin/env python3
"""DIE-QC-45: core-tap pin rects (materialized ODB masters, die frame) vs the clock tree tap xy (tree.json, where the
fixed drop lands).  usage: tap_pin_check.py INSTS MASTERS TREE TAPS_TXT OUT"""
import sys, json, collections
fi, fm, ft, fx, fo = sys.argv[1:6]
I = {d["name"]: d for d in json.load(open(fi))["insts"]}; M = json.load(open(fm)); T = json.load(open(ft))
def xf(d, r):
    w, h = M[d["master"]]["size"]; bx, by = d["bbox"][:2]; o = d["orient"]; x0, y0, x1, y1 = r
    if o in ("MY", "R180"): x0, x1 = w - x1, w - x0
    if o in ("MX", "R180"): y0, y1 = h - y1, h - y0
    return (bx + x0, by + y0, bx + x1, by + y1)
pm = {}
for m, v in M.items():
    dd = collections.defaultdict(list)
    for nm, L, *r in v["pins"]: dd[nm].append((L, r))
    pm[m] = dd
tx = {}
for l in open(fx):
    t, inst, pin, x, y = l.split(); tx[t] = (inst, pin, float(x), float(y))
c = collections.Counter(); dist = []; ex = []
for t in T["taps"]:
    inst, pin, x, y = tx[t["port"]]
    d = I.get(inst)
    if d is None: c["no_inst"] += 1; continue
    rr = [xf(d, r) for L, r in pm[d["master"]].get(pin, [])]
    if not rr: c["no_pin"] += 1; continue
    dmin = min(max(r[0] - x, x - r[2], 0) + max(r[1] - y, y - r[3], 0) for r in rr)
    dist.append(dmin); c["inside" if dmin <= 1e-4 else "outside"] += 1
    if dmin > 1e-4 and len(ex) < 6: ex.append([t["port"], inst, pin, x, y, [round(v, 4) for v in rr[0]], round(dmin, 4)])
dist.sort()
r = dict(taps=len(T["taps"]), verdict=dict(c), dist_max_um=round(dist[-1], 4) if dist else None,
         hist={k: sum(1 for v in dist if lo < v <= hi) for k, (lo, hi) in dict(le0=(-1, 1e-4), le20nm=(1e-4, .0201), le40nm=(.0201, .0401), gt40nm=(.0401, 1e9)).items()},
         examples=ex)
json.dump(r, open(fo, "w"), indent=1); print(json.dumps(r, indent=1))
