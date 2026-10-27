#!/usr/bin/env python3
"""HBM-CORE-LAT-R4 placed render: render_r4.py placed.csv master_slice.json OUTLINE_W OUTLINE_H TRUNK_CELL_W N OUT.png TITLE"""
import csv, json, sys
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
pc, ms, W, H, cw, n, out, title = sys.argv[1], sys.argv[2], float(sys.argv[3]), float(sys.argv[4]), float(sys.argv[5]), int(sys.argv[6]), sys.argv[7], sys.argv[8]
rows = list(csv.DictReader(open(pc)))
fig, ax = plt.subplots(figsize=(9, 9))
ax.add_patch(Rectangle((0, 0), W, H, fill=False, lw=1.2, ec="k"))
col = dict(std="#bbbbbb", buf="#8fbf8f", ff="#1f5fbf", macro="#d08040", tap="#eeeeee")
cnt = {}
for r in rows:
    k = r["kind"]; cnt[k] = cnt.get(k, 0) + 1
    if k == "pin":
        ax.plot(float(r["x"]), float(r["y"]), ".", ms=2, color="#c02020")
        continue
    if k == "tap":
        continue
    ax.add_patch(Rectangle((float(r["x"]), float(r["y"])), float(r["w"]), float(r["h"]), lw=0, fc=col.get(k, "#999")))
s = json.load(open(ms))
for isl in s["islands"]:
    x0, y0, x1, y1 = isl["rect_um"]
    ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fill=False, lw=1.5, ec="#e000e0"))
    cx, cy = isl["clock_pin"]["xy_um"]
    ax.plot(cx, cy, "*", ms=14, color="#e000e0")
    # planned trunk sites (ot_trunk_r4.tcl: centre row, abutted from x0 + 1 site)
    rh = 0.27
    ry = y0 + round(((y0 + y1) / 2 - y0) / rh - 0.5) * rh
    for i in range(n):
        ax.add_patch(Rectangle((x0 + 0.054 + i * cw, ry), cw, rh, fc="#ff00ff", ec="k", lw=0.3))
ax.set_xlim(-2, W + 2); ax.set_ylim(-2, H + 2); ax.set_aspect("equal")
ax.set_title(f"{title}\n" + " ".join(f"{k}={v}" for k, v in sorted(cnt.items())) + f"  trunk {n} planned (magenta) in entry island", fontsize=9)
fig.savefig(out, dpi=130, bbox_inches="tight")
