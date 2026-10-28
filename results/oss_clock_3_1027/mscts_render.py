#!/usr/bin/env python3
"""Render an mscts region tree (tree.json wire_pts + buffers) over the region keepouts; count buffers inside keepouts.
usage: mscts_render.py tree.json spec.json out.png [x0 y0 x1 y1 zoom-window]"""
import json, sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

t, s, out = json.load(open(sys.argv[1])), json.load(open(sys.argv[2])), sys.argv[3]
win = [float(v) for v in sys.argv[4:8]] if len(sys.argv) >= 8 else None
ko = s["keepouts"]
inside = lambda p: any(k[0] < p[0] < k[2] and k[1] < p[1] < k[3] for k in ko)
fig, ax = plt.subplots(figsize=(10, 14) if not win else (10, 10), dpi=110)
for k in ko:
    ax.add_patch(Rectangle((k[0], k[1]), k[2] - k[0], k[3] - k[1], fc="#d9d9d9", ec="#888", lw=0.4))
for pts in t["wire_pts"].values():
    ax.plot([p[0] for p in pts], [p[1] for p in pts], color="#1f5fa8", lw=0.5)
bad = 0
for n, b in t["buffers"].items():
    if b.get("kind") == "sink":
        ax.plot(*b["xy"], marker=".", ms=2, color="#2a9d3a")
    else:
        bi = inside(b["xy"]); bad += bi
        ax.plot(*b["xy"], marker="s", ms=4 if bi else 1.6, color="#d62728" if bi else "#e08a00")
for sn in t.get("snakes", []):
    ax.plot(*sn["at"], marker="o", ms=3, mfc="none", color="#9b3cc4")
if win:
    ax.set_xlim(win[0], win[2]); ax.set_ylim(win[1], win[3])
ax.set_aspect("equal")
ax.set_title(f"{t['region']}: {len(t['buffers'])} nodes, wire {t['wirelength_um']/1000:.1f} mm, "
             f"buffers in keepouts {bad}  (grey keepout, blue wire, orange repeater/buffer, green sink, purple snake)",
             fontsize=7)
fig.savefig(out, bbox_inches="tight")
print("buffers_in_keepouts", bad)
