#!/usr/bin/env python3
"""render_s81_locality.py PLAN OUT.json(from s81_locality.py) PNG : proposed regions (colour), feed tree not drawn,
crossings as lines part-centre to part-centre: green margin>=100, red <100 (estimate)."""
import json, sys, random
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
P = json.load(open(sys.argv[1])); o = json.load(open(sys.argv[2])); T = P["partition_types"]
reg = o["proposed_map"]; rows = o["proposed_rows"]
random.seed(3); col = {r: (random.random(), random.random(), random.random()) for r in sorted(set(reg.values()))}
fig, ax = plt.subplots(figsize=(16, 12.6)); cen = {}
for p in P["partitions"]:
    w, h = T[p["type"]]["outline_um"]; x, y = p["origin_um"]
    if p.get("orient", "R0") in ("R90", "R270", "MXR90", "MYR90"): w, h = h, w
    cen[p["name"]] = (x + w / 2, y + h / 2)
    ax.add_patch(Rectangle((x / 1000, y / 1000), w / 1000, h / 1000, fc=col[reg[p["name"]]] + (0.55,), ec="k", lw=0.3))
for r in sorted(rows, key=lambda r: r["margin_ps"] < 100):
    a, b = cen[r["src"]], cen[r["dst"]]; bad = r["margin_ps"] < 100
    ax.plot([a[0] / 1000, b[0] / 1000], [a[1] / 1000, b[1] / 1000], color="red" if bad else "green",
            lw=2.2 if bad else 0.8, alpha=0.9 if bad else 0.6)
W, H = P["die"]["outline_um"]; ax.set_xlim(0, W / 1000); ax.set_ylim(0, H / 1000); ax.set_aspect("equal")
e = o["proposed_linkfeed"]; s = o["proposed"]
ax.set_title(f"S81 locality estimate: {s['regions']} connectivity regions (span<={o['input']['span_mm']} mm), bits inside {s['bits_inside_pct']}%, "
             f"link-following SPT feed @ {o['input']['ps_mm']} ps/mm: {e['margin_lt_100']}/{e['crossings']} crossings margin<100 (red)", fontsize=10)
ax.set_xlabel("mm"); fig.tight_layout(); fig.savefig(sys.argv[3], dpi=80)
