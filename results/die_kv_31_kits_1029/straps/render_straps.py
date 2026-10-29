#!/usr/bin/env python3
"""render a kit's plan pins (strap pins red) + plan macros/keepouts; full view + zoom on the strap row.
usage: render_straps.py PLAN TYPE PLAN_PINS OUT.png"""
import json, sys
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
P = json.load(open(sys.argv[1])); tn = sys.argv[2]; t = P["partition_types"][tn]
pins = json.load(open(sys.argv[3]))["pins"]
W, H = t["outline_um"]
fig, axs = plt.subplots(1, 2, figsize=(18, 7), gridspec_kw=dict(width_ratios=[1.4, 1]))
for ax, (x0, x1, y0, y1) in zip(axs, [(-20, W + 20, -20, H + 20), (0, 380, -2, 30)]):
    ax.add_patch(Rectangle((0, 0), W, H, fill=False, ec="k"))
    for c in t.get("contents", []):
        if c.get("origin_um") and c.get("outline_um"):
            ax.add_patch(Rectangle(tuple(c["origin_um"]), *c["outline_um"], fc="#cfe0ff", ec="b", lw=0.6))
    for r in (t.get("clock", {}).get("keepouts_um") or []):
        ax.add_patch(Rectangle((r[0], r[1]), r[2] - r[0], r[3] - r[1], fill=False, ec="orange", hatch="//", lw=0.6))
    o = [p for p in pins if not p["name"].startswith("strap_")]; s = [p for p in pins if p["name"].startswith("strap_")]
    ax.scatter([p["x"] for p in o], [p["y"] for p in o], s=2, c="gray", label=f"other pins {len(o)}")
    ax.scatter([p["x"] for p in s], [p["y"] for p in s], s=6, c="red", label=f"strap pins {len(s)} (M7)")
    ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); ax.set_aspect("equal" if ax is axs[0] else "auto"); ax.legend(loc="upper right", fontsize=8)
axs[0].set_title(f"{tn} {W}x{H} um: plan pins + macros"); axs[1].set_title("zoom: south strap row y=4.32")
fig.tight_layout(); fig.savefig(sys.argv[4], dpi=110)
