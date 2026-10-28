#!/usr/bin/env python3
"""feed json for die_trial --tree-form link_htree/link_fishbone ({root, parent, tap{'p->c': xy}, joined}) + region map
({part_region}) from a retree/anneal feed (taps = locality.tap_points: bit-weighted crossing centroid per pair).
usage: mkfeed.py REPO PLAN BIND FEEDJ OUTFEED OUTMAP"""
import json, sys
from pathlib import Path
repo, planp, bindp, fj, of, om = sys.argv[1:7]
sys.path.insert(0, f"{repo}/tools/die_plan")
import locality as L
D = L.load_plan(planp)
b = json.loads(Path(bindp).read_text())
reg = {p: x["region"] for p, x in b["parts"].items() if isinstance(x, dict) and x.get("region")}
for p in D["parts"]: reg.setdefault(p, p)
padj = L.part_adjacency(D); G = L.region_geom(D, reg); X = L.crossings(D, reg, G, padj); taps = L.tap_points(G, X)
f = json.load(open(fj))
tap = {f"{p}->{c}": [round(v, 1) for v in (taps.get((p, c)) or L.xing_point(G[p]["bbox"], G[c]["bbox"]))]
       for c, p in f["parent"].items() if p}
json.dump(dict(root=f["root"], parent=f["parent"], tap=tap, joined=[]), open(of, "w"), indent=0)
json.dump(dict(part_region=reg), open(om, "w"), indent=0)
print("regions", len(f["parent"]), "edges", len(tap), "parts", len(reg))
