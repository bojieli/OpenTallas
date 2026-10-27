#!/usr/bin/env python3
"""render r12_top_sites.json (cell sites + top-tree nets) over the plan partitions/hard cores. usage: PLAN SITES OUT.png [x0 y0 x1 y1]"""
import json, sys
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
P = json.load(open(sys.argv[1])); S = json.load(open(sys.argv[2])); out = sys.argv[3]
box = [float(v) for v in sys.argv[4:8]] if len(sys.argv) >= 8 else None
T = P["partition_types"]
fig, ax = plt.subplots(figsize=(16, 13.5) if not box else (12, 10), dpi=110)
for p in P["partitions"]:
    t = T[p["type"]]; (x, y), (w, h) = p["origin_um"], t["outline_um"]
    ax.add_patch(Rectangle((x, y), w, h, fill=False, lw=0.3, ec="#888"))
    for hc in t.get("hard_cores", []):
        (hx, hy), (hw, hh) = hc["origin_um"], hc["outline_um"]
        o = p.get("orient", "R0")
        X = x + (w - hx - hw if o in ("MY", "R180") else hx); Y = y + (h - hy - hh if o in ("MX", "R180") else hy)
        ax.add_patch(Rectangle((X, Y), hw, hh, fc="#f2d7d5", ec="none"))
g = {}
for n, c in S["cell_sites"].items():
    g.setdefault(c["group"], c)
bad = set()
for k, v in S["summary"]["gate"]["examples"].items():
    for r in v: bad.add(tuple(r["origin_um"]))
for e in S["nets"]:
    a, b = g[int(e["drv"][1:])], g[int(e["load"][1:])]
    ax.plot([a["origin_um"][0], b["origin_um"][0]], [a["origin_um"][1], b["origin_um"][1]],
            c="#1f4e9c" if e["layer"] == "M9" else "#2e8b57", lw=0.9 if e["layer"] == "M9" else 0.5)
col = {"top_node": "#d62728", "top_rep": "#444", "col_tap": "#ff7f0e"}
for k, cc in col.items():
    pts = [c["origin_um"] for c in g.values() if c["kind"] == k]
    ax.scatter([p[0] for p in pts], [p[1] for p in pts], s=4 if k == "top_rep" else 9, c=cc, label=f"{k} ({len(pts)} groups)", zorder=3)
ax.scatter([p[0] for p in bad], [p[1] for p in bad], s=80, facecolors="none", edgecolors="m", zorder=4, label="gate example")
W, H = P["die"]["outline_um"]
ax.set_xlim(*(box[0::2] if box else (0, W))); ax.set_ylim(*(box[1::2] if box else (0, H))); ax.set_aspect("equal")
ax.legend(loc="upper right", fontsize=8)
s = S["summary"]
ax.set_title(f"R12 mesh3 top tree on per-type island lattice: {s['groups']} groups / {s['instances']} BUFx24, nets M8 {s['nets_by_layer'].get('M8')} / M9 {s['nets_by_layer'].get('M9')}; "
             f"gate {s['gate']['errors']} overlaps {s['gate']['overlaps']} (UNCHECKED)", fontsize=8)
fig.savefig(out, bbox_inches="tight")
