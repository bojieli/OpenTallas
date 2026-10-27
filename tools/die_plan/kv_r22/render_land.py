#!/usr/bin/env python3
"""CLOCK-KV-R22: render the declared ft0 landing islands at PHY boundaries (die frame), zoom on 2 boundaries.
usage: render_land.py PLAN.json OUT.png"""
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

import schema as S

P = S.Plan(S.load(sys.argv[1]))
fig, axs = plt.subplots(1, 3, figsize=(18, 6))
views = [("WS_7 -> WS_6 boundary (R0)", "phy_WS_6", "phy_WS_7"), ("WN_7 -> WN_6 boundary (MX)", "phy_WN_6", "phy_WN_7"),
         ("EN_7 -> EN_6 boundary (R180)", "phy_EN_6", "phy_EN_7")]


def die_rect(part, r):
    a = P.to_die(part, (r[0], r[1])); b = P.to_die(part, (r[2], r[3]))
    return min(a[0], b[0]), min(a[1], b[1]), abs(a[0] - b[0]), abs(a[1] - b[1])


for ax, (title, rx, tx) in zip(axs, views):
    for part, col in ((rx, "#cfe3ff"), (tx, "#ffe3cf")):
        r = P.rect(part)
        ax.add_patch(Rectangle((r[0], r[1]), r[2] - r[0], r[3] - r[1], fc=col, ec="k", lw=1))
        t = P.ptype(part)
        for isl in t.get("landing_islands", []):
            x, y, w, h = die_rect(part, isl["rect_um"])
            ax.add_patch(Rectangle((x, y), w, h, fc="red", ec="darkred", lw=1.5, zorder=5))
            ax.annotate(f"{part} {isl['name']} {sum(isl['cells'].values())} HB4", (x + w, y + h), fontsize=7,
                        color="darkred")
        for ci in t.get("clock", {}).get("die_islands_um", []):
            x, y, w, h = die_rect(part, ci)
            ax.add_patch(Rectangle((x, y), w, h, fc="green", ec="green", zorder=4))
    for pid, pr in P.ports.items():
        if pr["dst"]["part"] == rx and pr["dst"]["bus"] == "ft0_i":
            lo, hi = pr["window_um"]
            rr = P.rect(rx)
            yb = rr[3] if P.rect(tx)[1] >= rr[3] - 1 else rr[1]
            ax.plot([lo, hi], [yb, yb], color="blue", lw=6, zorder=6)
            ax.annotate(f"{pid} ft0 window", (hi, yb), fontsize=7, color="blue")
            cx = (lo + hi) / 2
    rr, rt = P.rect(rx), P.rect(tx)
    yb = rr[3] if rt[1] >= rr[3] - 1 else rr[1]
    ax.set_xlim(cx - 12, cx + 12); ax.set_ylim(yb - 8, yb + 8); ax.set_aspect("equal")
    ax.set_title(f"{title}\nblue=ft0 window, red=landing island (receiver {rx}), green=die clock islands", fontsize=8)
fig.tight_layout()
fig.savefig(sys.argv[2], dpi=110)
