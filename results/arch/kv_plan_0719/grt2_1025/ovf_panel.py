#!/usr/bin/env python3
"""PATH-KV-GRT2: side-by-side W-column overflow maps (congestion.rpt gcells) over partitions + hard cores.
usage: ovf_panel.py PLAN OUT.png label=congestion.rpt ..."""
import sys, re, json
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
plan = json.load(open(sys.argv[1])); T = plan["partition_types"]
runs = [a.split("=", 1) for a in sys.argv[3:]]
X0, X1, Y0, Y1 = 1500, 5200, 11900, 27100
fig, axs = plt.subplots(1, len(runs), figsize=(4.2 * len(runs), 14), sharey=True)
for ax, (lab, f) in zip(axs, runs):
    for p in plan["partitions"]:
        t = T[p["type"]]; w, h = t["outline_um"]; ox, oy = p["origin_um"]; o = p.get("orient", "R0")
        if ox > X1 or ox + w < X0 or oy > Y1 or oy + h < Y0: continue
        ax.add_patch(Rectangle((ox, oy), w, h, fill=False, ec="0.5", lw=0.6))
        ax.text(ox + 20, oy + h - 120, p["name"], fontsize=6, color="0.3")
        for c in t.get("hard_cores", []):
            cx, cy = c["origin_um"]; cw, ch = c["outline_um"]
            if o in ("MX", "R180"): cy = h - cy - ch
            if o in ("MY", "R180"): cx = w - cx - cw
            ax.add_patch(Rectangle((ox + cx, oy + cy), cw, ch, fc="0.85", ec="none"))
    tot = 0
    for v in open(f).read().split("violation type:")[1:]:
        m = re.search(r"congestion:(\d+)", v); b = re.search(r"bbox = \(([\d.]+), ([\d.]+)\) - \(([\d.]+), ([\d.]+)\)", v)
        c = int(m.group(1)); x0, y0, x1, y1 = map(float, b.groups()); tot += 1
        col = "tab:red" if v.strip().startswith("Horizontal") else "tab:blue"
        s = 40 + 10 * min(c, 16)
        ax.add_patch(Rectangle((x0 - s / 2, y0 - s / 2), s, s, fc=col, ec="none", alpha=0.75))
    ax.set_xlim(X0, X1); ax.set_ylim(Y0, Y1); ax.set_aspect("equal")
    ax.set_title(f"{lab}\n{tot} overflow gcells (red H / blue V)", fontsize=8); ax.tick_params(labelsize=6)
plt.tight_layout(); plt.savefig(sys.argv[2], dpi=110)
