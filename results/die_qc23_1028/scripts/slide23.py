"""DIE-QC-23: repeater slide off the planned leg (ctree.tcl place vs tree route/snake polyline), per trial.
usage: slide23.py TRIAL [TRIAL ...]"""
import json, re, sys, collections
def dseg(p, a, b):
    (x, y), (x0, y0), (x1, y1) = p, a, b
    cx = min(max(x, min(x0, x1)), max(x0, x1)); cy = min(max(y, min(y0, y1)), max(y0, y1)); return abs(x - cx) + abs(y - cy)
for K in sys.argv[1:]:
    T = json.load(open(f"{K}/clock/tree.json")); N = {int(k): v for k, v in T["nodes"].items()}
    pl = collections.defaultdict(list)
    for l in open(f"{K}/clock/ctree.tcl"):
        m = re.match(r"place_inst -name r(\d+)_(\d+) -location \{([\d.]+) ([\d.]+)\}", l)
        if m: pl[int(m.group(1))].append((float(m.group(3)), float(m.group(4))))
    sl = []; per = collections.defaultdict(float)
    for k, cells in pl.items():
        nd = N.get(k)
        if not nd or nd.get("parent") is None: continue
        p = N[nd["parent"]]
        pts = ([(p["x"], p["y"])] + [tuple(x) for x in nd["snake"]] + [(nd["x"], nd["y"])]) if nd.get("snake") else \
              ([tuple(x) for x in nd["route"]] if nd.get("route") else [(p["x"], p["y"]), (nd["x"], nd["y"])])
        pts = [(p["x"], p["y"])] + pts + [(nd["x"], nd["y"])]
        for c in cells:
            d = min(dseg(c, a, b) for a, b in zip(pts, pts[1:])); sl.append((d, k, nd.get("dme")))
    s = sorted(x[0] for x in sl); dm = [x for x in sl if x[2]]
    print(K, "cells", len(s), "slide>50", sum(x > 50 for x in s), ">100", sum(x > 100 for x in s), "max", round(s[-1], 1),
          "| in DME regions >50", sum(x[0] > 50 for x in dm), "regions", len({x[2] for x in dm if x[0] > 50}),
          "worst", [(round(d, 1), k, r) for d, k, r in sorted(sl, reverse=True)[:3]])
