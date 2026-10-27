#!/usr/bin/env python3
"""INFRA-FIRST-HEAD-1 R1: island-lattice census for the s81_head infra-first plan event (12.2a1 / 12.2c).
Reads the plan, applies the R1 plan-delta core geometry (rebuilt lattice outlines elemA 319.68 / elemB 285.12, eB
origin x 216.0 -> 211.68 so its centre sits on the tile MY axis), and reports for every partition type the die-frame
positions of its in-core clock-entry islands (core centres) per instance, plus whether those land on one die column /
row lattice in every orientation.  Read-only; prints JSON."""
import json, sys, collections
P = json.load(open(sys.argv[1]))
OUT = {"elemA": 319.68, "elemB": 285.12}
EB_X = float(sys.argv[2]) if len(sys.argv) > 2 else 211.68
def tf(q, w, h, x, y):
    o = q["orient"]; ox, oy = q["origin_um"]
    if o == "R0": return ox + x, oy + y
    if o == "MY": return ox + w - x, oy + y
    if o == "MX": return ox + x, oy + h - y
    if o == "R180": return ox + w - x, oy + h - y
    raise ValueError(o)
types = P["partition_types"]; res = {}
for tn, t in types.items():
    w, h = t["outline_um"]
    ents = []
    for c in t.get("hard_cores", []):
        s = OUT["elemB"] if "elemB" in c["module"] else OUT["elemA"]
        ox, oy = c["origin_um"]
        if "elemB" in c["module"]: ox = EB_X
        ents.append((c["inst"].split(".")[-1], ox + s / 2, oy + s / 2))
    if not ents:     # soft type: one island at the type-frame centre (R1 default, refined per type in R2)
        ents = [("centre", w / 2, h / 2)]
    inst = [q for q in P["partitions"] if q["type"] == tn]
    # MY/MX invariance of the type-frame island set
    sym = {}
    for o, f in (("MY", lambda x, y: (w - x, y)), ("MX", lambda x, y: (x, h - y)), ("R180", lambda x, y: (w - x, h - y))):
        if any(q["orient"] == o for q in inst):
            pts = sorted((round(x, 3), round(y, 3)) for _, x, y in ents)
            img = sorted((round(f(x, y)[0], 3), round(f(x, y)[1], 3)) for _, x, y in ents)
            sym[o] = max((abs(a[0] - b[0]) + abs(a[1] - b[1])) for a, b in zip(pts, img))
    res[tn] = dict(n=len(inst), orients=dict(collections.Counter(q["orient"] for q in inst)),
                   islands_frame=[[e[0], round(e[1], 3), round(e[2], 3)] for e in ents], orient_asym_um=sym,
                   die_xy=[[q["name"]] + [list(map(lambda v: round(v, 3), tf(q, w, h, x, y))) for _, x, y in ents] for q in inst])
# column / row lattice of hd_tile islands
xs = sorted({p[0] for r in res["hd_tile"]["die_xy"] for p in r[1:]})
ys = sorted({p[1] for r in res["hd_tile"]["die_xy"] for p in r[1:]})
dx = sorted({round(b - a, 3) for a, b in zip(xs, xs[1:])})
summary = {"hd_tile_island_cols": len(xs), "col_pitches": dx, "hd_tile_island_rows": len(ys),
           "row_pitches": sorted({round(b - a, 3) for a, b in zip(ys, ys[1:])}),
           "types": {k: dict(n=v["n"], orients=v["orients"], islands=len(v["islands_frame"]), orient_asym_um=v["orient_asym_um"])
                     for k, v in res.items()}}
json.dump(dict(summary=summary, detail=res), open(sys.argv[3] if len(sys.argv) > 3 else "/dev/stdout", "w"), indent=1)
print(json.dumps(summary, indent=1))
