#!/usr/bin/env python3
"""QC-A0 10-24: render an A0 v7 kit for review: outline, hard children (+ 8.64-um tap clearance), regions, R4 grid
taps (stars), v6 sink-anchored additions (dots, sized by v5 sinks), the 400-um grid cells, signal pin faces.
    render_a0c7.py nk|nl OUT.png"""
import json
import re
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
k, out = sys.argv[1], sys.argv[2]
fp = json.loads((ROOT / f"physical/ref_tile/qfd_tile_{k}_a0cv7/floorplan.json").read_text())
tp = json.loads((HERE / f"a0c7_{k}_taps.json").read_text())
W, H = fp["die"][2], fp["die"][3]
fig, ax = plt.subplots(figsize=(6, 13))
ax.add_patch(Rectangle((0, 0), W, H, fill=False, lw=1.5))
for b in fp["blocks"]:
    if b.get("kind") != "child":
        continue
    ax.add_patch(Rectangle((b["x"] - 8.64, b["y"] - 8.64), b["w"] + 17.28, b["h"] + 17.28, fc="none", ec="orange", ls=":", lw=0.6))
    ax.add_patch(Rectangle((b["x"], b["y"]), b["w"], b["h"], fc="#cfd8e3", ec="#456"))
for i in range(1, 2):
    ax.axvline(i * W / 2, color="grey", lw=0.5, ls="--")
for j in range(1, 3):
    ax.axhline(j * H / 3, color="grey", lw=0.5, ls="--")
pins = [l for l in (ROOT / f"tools/qwen_romleaf/a0core/qfd_tile_{k}_a0c7_pins.tcl").read_text().splitlines()
        if l.startswith("place_pin") and "ck" not in l.split("}")[0]]
xs = [tuple(map(float, re.search(r"-location \{([\d.]+) ([\d.]+)\}", l).groups())) for l in pins]
ax.scatter([x for x, _ in xs], [y for _, y in xs], s=0.3, c="green")
for t in tp["taps"]:
    x, y = t["xy"]
    if t["kind"] == "grid":
        ax.scatter([x], [y], marker="*", s=220, c="red", zorder=5)
    else:
        ax.scatter([x], [y], s=max(10, t["sinks_v5"] / 25), c="blue", alpha=0.7, zorder=4)
    ax.annotate(t["name"].replace("ck_t", ""), (x, y), fontsize=6, xytext=(3, 3), textcoords="offset points")
ax.set_xlim(-10, W + 10); ax.set_ylim(-10, H + 10); ax.set_aspect("equal")
ax.set_title(f"qfd_tile_{k}_a0cv7: {tp['grid']} grid taps (red *) + {tp['additions']} v6 sink taps (blue, size ~ v5 sinks)", fontsize=8)
fig.savefig(out, dpi=130, bbox_inches="tight")
print(out)
