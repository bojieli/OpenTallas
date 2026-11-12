#!/usr/bin/env python3
"""tapcheck.py REPO PLAN TYPE: legality of every added tap (taps.grid_explicit_sites rule); for an illegal one, the
nearest legal spot on a 2.16 grid within 60 um."""
import json, sys
from pathlib import Path
repo = Path(sys.argv[1]); sys.path.insert(0, str(repo / "tools/die_plan"))
import schema
from placement_obstacles import placement_boxes
P = json.load(open(sys.argv[2])); tn = sys.argv[3]
typ = P["partition_types"][tn]
class PP: pass
pp = PP(); pp.types = P["partition_types"]; pp.raw = P
try:
    grid = schema._grid_taps(pp, tn)
except Exception as e:
    print("grid err", e); grid = []
clear = schema.TAP_CLEAR_UM
w, h = typ["outline_um"]
boxes = placement_boxes(typ, halo=clear)
def legal(x, y, taken):
    if not (clear <= x <= w - clear and clear <= y <= h - clear): return "outline"
    for a, b in taken:
        if abs(x - a) < clear and abs(y - b) < clear: return "spacing %s" % ((a, b),)
    for k, (a, b, c, d) in boxes.items():
        if a < x < c and b < y < d: return "box %s" % k
    return None
taken = [(x, y) for _, x, y in grid]
for g in grid:
    r = legal(g[1], g[2], [])
    if r and r.startswith("box"): print("GRID", g, r)
for p in typ["clock"].get("added_taps") or []:
    x, y = p["xy"]; r = legal(x, y, taken)
    if r:
        best = None
        for i in range(-28, 29):
            for j in range(-28, 29):
                X, Y = x + 2.16 * i, y + 2.16 * j
                if legal(X, Y, taken) is None:
                    d = abs(X - x) + abs(Y - y)
                    if best is None or d < best[0]: best = (d, round(X, 2), round(Y, 2))
        print("ADDED", p["name"], p["xy"], r, "-> nearest legal", best)
    taken.append((x, y))
print("checked", len(grid), "grid +", len(typ["clock"].get("added_taps") or []), "added")
