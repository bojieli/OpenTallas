#!/usr/bin/env python3
"""DIE-QC: render the ROUTED die clock (GRT guides of the clock nets: ck_* tree nets + t_* tap nets) over the
partition outlines and hard-core halos (SiteMap forbidden rects), tree cells as dots; cells inside a forbidden rect red.
usage: render_clk.py WT PLAN RUN_DIR CORNER OUT_PNG"""
import json, sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
wt, plan, run, C, png = sys.argv[1:6]
sys.path.insert(0, wt + "/tools/die_plan")
import schema as S, die_trial as DT
P = S.Plan(S.load(plan))
site = DT.SiteMap(P)
T = json.load(open(run + "/clk/tree.json"))
rects = {"M8": [], "M9": [], "other": []}
cur, keep = None, False
dbu = None
with open(f"{run}/out_{C}/route_{C}.guide") as f:
    for ln in f:
        s = ln.strip()
        if not s or s == "(":
            continue
        if s == ")":
            cur = None; continue
        x = s.split()
        if len(x) == 1:
            cur = x[0]; keep = cur.startswith("ck_") or cur.startswith("t_") or cur == "root"; continue
        if keep and len(x) == 5:
            rects.get(x[4], rects["other"]).append(tuple(map(int, x[:4])))
allx = max(max(r[2] for r in v) for v in rects.values() if v)
dbu = 1000.0 if allx > P.W * 500 else 1.0
fig, ax = plt.subplots(figsize=(24, 20.5))
for n, p in P.parts.items():
    w, h = P.types[p["type"]]["outline_um"]; ox, oy = p["origin_um"]
    ax.add_patch(Rectangle((ox, oy), w, h, fill=False, lw=0.3, ec="0.6"))
for r in site.forb:
    ax.add_patch(Rectangle((r[0], r[1]), r[2] - r[0], r[3] - r[1], fill=True, lw=0, fc="#f2d0a0", alpha=0.6))
for L, col in (("M9", "#c03030"), ("M8", "#2050c0"), ("other", "#30a030")):
    for a, b, c, d in rects[L]:
        ax.add_patch(Rectangle((a / dbu, b / dbu), (c - a) / dbu, (d - b) / dbu, fill=True, lw=0, fc=col, alpha=0.5))
bad = [(x, y) for x, y in T["sites"].values() if site.why((x, y))]
xs = [v[0] for v in T["sites"].values()]; ys = [v[1] for v in T["sites"].values()]
ax.scatter(xs, ys, s=0.3, c="k")
if bad:
    ax.scatter([b[0] for b in bad], [b[1] for b in bad], s=60, c="r", marker="x")
ax.set_xlim(0, P.W); ax.set_ylim(0, P.H); ax.set_aspect("equal")
ax.set_title(f"QC die clock ROUTED (combo GRT {C}): guides M8 blue / M9 red / other green; {len(T['sites'])} cells, "
             f"{len(bad)} on forbidden; core halos tan")
fig.savefig(png, dpi=110, bbox_inches="tight")
print("guides", {k: len(v) for k, v in rects.items()}, "bad", len(bad), "dbu", dbu)
