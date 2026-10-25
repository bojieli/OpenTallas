#!/usr/bin/env python3
"""Render the root bottom band (hard cores + ROOTEP re-routed chains + old placeholder chains for comparison)."""
import json, sys
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
new, old, png = sys.argv[1:4]
Y1 = float(sys.argv[4]) if len(sys.argv) > 4 else 2500
BUS = ["L12_o", "L12m_o", "L13_o", "L13m_o", "L62_o", "L62m_o", "L74m_i", "L89_i", "L89m_i"]
fig, axs = plt.subplots(1, 2, figsize=(18, 14))
for ax, path, ttl in ((axs[0], old, "BEFORE (B2o cartesian placeholder)"), (axs[1], new, "AFTER (ROOTEP typed endpoints)")):
    t = json.load(open(path))["partition_types"]["root"]
    W, H = t["outline_um"]
    ax.add_patch(Rectangle((0, 0), W, H, fill=False, lw=1.5))
    for h in t["hard_cores"]:
        x, y = h["origin_um"]; w, hh = h["outline_um"]
        if y > Y1: continue
        ax.add_patch(Rectangle((x, y), w, hh, fc="#d9d9d9", ec="k", lw=0.6))
        ax.text(x + w / 2, y + hh / 2, h["inst"].replace("u_", "").replace("hc_eng_", "hc:").replace("tkm_SW_", "tkm:"),
                fontsize=6, ha="center", va="center")
    for c in t["contents"]:
        if c["inst"] == "u_tkx_rx_SW":
            x, y = c["origin_um"]; w, hh = c["outline_um"]
            ax.add_patch(Rectangle((x, y), w, hh, fc="none", ec="purple", ls="--"))
    cols = plt.cm.tab10.colors
    seen = set()
    for e in t.get("internal_stations", []):
        b = e.get("conn", "")[4:]
        if b not in BUS: continue
        pts = [e["from_um"]] + e["regs_um"] + [e["to_um"]]
        xs, ys = [], []
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            xs += [x0, x1, x1]; ys += [y0, y0, y1]
        col = cols[BUS.index(b)]
        lw = 0.5 + 3.0 * min(e.get("bits", 1), 2200) / 2200
        ax.plot(xs, ys, color=col, lw=lw, alpha=0.7, label=b if b not in seen else None)
        seen.add(b)
        ax.scatter([p[0] for p in e["regs_um"]], [p[1] for p in e["regs_um"]], s=6, color=col, zorder=3)
    ax.axhline(1067.04, color="r", ls=":", lw=1); ax.text(W * 0.7, 1080, "cut y=1067", color="r", fontsize=8)
    ax.set_xlim(-60, W + 60); ax.set_ylim(-30, Y1); ax.set_aspect("equal"); ax.set_title(ttl)
    ax.legend(fontsize=7, loc="upper right")
plt.tight_layout(); plt.savefig(png, dpi=110)
