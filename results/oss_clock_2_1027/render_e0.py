#!/usr/bin/env python3
"""render one mscts build (tree.json) over the spec keepouts: render_e0.py BUILD_DIR SPEC.json OUT.png"""
import json
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

d, sp, out = sys.argv[1:4]
t = json.load(open(f"{d}/tree.json"))
s = json.load(open(sp))
fig, ax = plt.subplots(figsize=(5, 14))
for r in s["keepouts"]:
    ax.add_patch(Rectangle((r[0], r[1]), r[2] - r[0], r[3] - r[1], color="#bbbbbb", lw=0))
B = t["buffers"]
for w in t["wires"]:
    a, b = B[w["drv"]]["xy"], B[w["load"]]["xy"]
    ax.plot([a[0], b[0], b[0]], [a[1], a[1], b[1]], color="#1f77b4", lw=0.6)
col = {"rep": "#2ca02c", "merge": "#d62728", "sink": "#000000", "root": "#ff7f0e"}
for k, v in B.items():
    ax.plot(*v["xy"], marker="o" if v["kind"] != "rep" else ".", ms=3 if v["kind"] != "rep" else 2, color=col.get(v["kind"], "m"))
x0, x1 = s["x_range"]
ax.set_xlim(x0 - 50, x1 + 50)
ax.set_ylim(-100, 26400)
ax.set_aspect("equal")
sm = t["summary"]
ax.set_title(f"{s['name']} [{t['objective']}]\nskew TT {sm['skew_TT_ps']} / FF {sm['skew_FF_ps']} ps (model), "
             f"grey = keepouts (cores+halo)\nred merge, green repeater, black tap", fontsize=7)
fig.tight_layout()
fig.savefig(out, dpi=110)
