#!/usr/bin/env python3
"""INFRA-FIRST-HEAD-2: die-frame census of the hd_tile plan core clock taps (the 12.8a entries) in every instance:
orient invariance of the type-frame tap set, die column / row lattice.  Read-only."""
import json, sys, collections
P = json.load(open(sys.argv[1]))
t = P["partition_types"]["hd_tile"]
w, h = t["outline_um"]
pts = [tuple(tp["xy"]) for tp in t["clock"]["taps"] if tp["kind"] == "core"]
def tf(q, x, y):
    o = q["orient"]; ox, oy = q["origin_um"]
    return {"R0": (ox + x, oy + y), "MY": (ox + w - x, oy + y), "MX": (ox + x, oy + h - y), "R180": (ox + w - x, oy + h - y)}[o]
inst = [q for q in P["partitions"] if q["type"] == "hd_tile"]
asym = {}
for o, f in (("MY", lambda x, y: (w - x, y)), ("MX", lambda x, y: (x, h - y)), ("R180", lambda x, y: (w - x, h - y))):
    if any(q["orient"] == o for q in inst):
        a = sorted((round(x, 3), round(y, 3)) for x, y in pts)
        b = sorted((round(f(x, y)[0], 3), round(f(x, y)[1], 3)) for x, y in pts)
        asym[o] = round(max(abs(p[0] - q[0]) + abs(p[1] - q[1]) for p, q in zip(a, b)), 3)
die = [tf(q, x, y) for q in inst for x, y in pts]
xs = sorted({round(p[0], 3) for p in die}); ys = sorted({round(p[1], 3) for p in die})
mid = P["die"]["outline_um"][0] / 2
west = [x for x in xs if x < mid]
print(json.dumps(dict(instances=len(inst), orients=dict(collections.Counter(q["orient"] for q in inst)),
                      taps_per_tile=len(pts), orient_asym_um=asym, cols=len(xs), cols_west=len(west),
                      col_pitches=sorted({round(b - a, 3) for a, b in zip(xs, xs[1:])}), rows=len(ys),
                      row_pitches=sorted({round(b - a, 3) for a, b in zip(ys, ys[1:])}),
                      on_864_half=all(abs((x / 4.32) - round(x / 4.32)) < 1e-6 for x in xs + ys)), indent=1))
