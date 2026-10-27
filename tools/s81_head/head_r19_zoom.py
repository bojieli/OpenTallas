#!/usr/bin/env python3
"""HEAD-CORE-R19 review zooms: plan die.pg.grid M9 VDD/VSS stripes (width/pitch/offset of PLAN), the R19 clock M9
straps (cyan, 0.64-um lane) vs the reference (R18) strap centres (dashed grey), tree legs/nodes, and declared islands
(plan, olive; trial-delta slots, magenta).  head_r19_zoom.py PLAN TRIAL_PLAN TREE_DIR REF_STRAPS OUT.png x0 y0 x1 y1 TITLE"""
import json, sys
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
sys.path.insert(0, str(Path(__file__).resolve().parent))
import head_mesh_r3 as H  # noqa: E402

plan, trial, tree, ref, out = sys.argv[1:6]
x0, y0, x1, y1 = (float(v) for v in sys.argv[6:10])
title = sys.argv[10] if len(sys.argv) > 10 else ""
PL, PT = H.Plan(plan), H.Plan(trial)
S = json.loads((Path(tree) / "straps.json").read_text())
R = json.loads(Path(ref).read_text())
N = json.loads((Path(tree) / "tree_nodes.json").read_text())
g9 = next(g for g in PL.P["die"]["pg"]["grid"] if g["layer"] == "M9" and not g.get("region"))
fig, ax = plt.subplots(figsize=(12, 9), dpi=110)
p, w, off = g9["pitch_um"], g9["width_um"], g9["offset_um"]
k = int((x0 - off) // (p / 2)) - 1
while off + k * p / 2 < x1 + p:
    c = off + k * p / 2
    ax.add_patch(Rectangle((c - w / 2, y0), w, y1 - y0, fc="#f2b8b8" if k % 2 == 0 else "#b8c8f2", ec="none", alpha=0.6))
    k += 1
for pp in PL.parts:
    r = pp["rect"]
    ax.add_patch(Rectangle(r[:2], r[2] - r[0], r[3] - r[1], fill=False, lw=0.6, ec="tab:olive", ls=(0, (4, 3))))
for c in PL.cores:
    ax.add_patch(Rectangle(c[:2], c[2] - c[0], c[3] - c[1], fc="0.85", ec="0.5", lw=0.3))
for P_, col in ((PT, "magenta"), (PL, "tab:olive")):
    for pp in P_.parts:
        for r in P_.T[pp["type"]].get("clock", {}).get("die_islands_um", []) or []:
            a_, b_ = P_.to_die(pp, r[0], r[1]), P_.to_die(pp, r[2], r[3])
            xa, xb, ya, yb = min(a_[0], b_[0]), max(a_[0], b_[0]), min(a_[1], b_[1]), max(a_[1], b_[1])
            if xb >= x0 and xa <= x1 and yb >= y0 and ya <= y1:
                ax.add_patch(Rectangle((xa, ya), xb - xa, yb - ya, fill=False, ec=col, lw=1.0))
for L, f, lo, hi, kd in R:
    if L == "M9" and x0 <= f <= x1:
        ax.plot([f, f], [max(lo, y0), min(hi, y1)], color="0.3", lw=0.8, ls="--")
for L, f, lo, hi, kd in S:
    if L == "M9" and x0 - 1 <= f <= x1 + 1:
        ax.add_patch(Rectangle((f - 0.32, max(lo, y0)), 0.64, min(hi, y1) - max(lo, y0), fc="tab:cyan", ec="none"))
    if L == "M8" and y0 <= f <= y1:
        ax.add_patch(Rectangle((max(lo, x0), f - 0.32), min(hi, x1) - max(lo, x0), 0.64, fc="tab:blue", ec="none"))
by = {n["tag"]: n for n in N}
for n in N:
    if n.get("parent"):
        q = by[n["parent"]]["xy"]
        ax.plot([q[0], n["xy"][0]], [q[1], n["xy"][1]], color="tab:red", lw=1.2)
for n in N:
    ax.plot(*n["xy"], marker="o", ms=5, color="tab:green" if not n["kids"] else "tab:purple", ls="none")
    if x0 <= n["xy"][0] <= x1 and y0 <= n["xy"][1] <= y1:
        ax.text(n["xy"][0], n["xy"][1], " " + n["tag"], fontsize=6)
ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); ax.set_aspect("equal")
ax.set_title(title + "\nPG M9 VDD/VSS (pink/blue) %.2f@%.2f; clock M9 cyan (R19), dashed = R18 centre; islands olive "
             "(plan) / magenta (trial delta)" % (w, p), fontsize=8)
fig.tight_layout(); fig.savefig(out); plt.close(fig)
