#!/usr/bin/env python3
"""INFRA-FIRST-HEAD-2 render: s81_head partitions + hard cores + plan clock entries + qc_clk_mesh3 grid tree."""
import json, sys
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
P = json.load(open(sys.argv[1])); G = json.load(open(sys.argv[2])); out = sys.argv[3]
box = [float(v) for v in sys.argv[4].split(",")] if len(sys.argv) > 4 else None
fig, ax = plt.subplots(figsize=(14, 14 if not box else 9), dpi=110)
def tf(q, w, h, x, y):
    o = q["orient"]; ox, oy = q["origin_um"]
    return {"R0": (ox + x, oy + y), "MY": (ox + w - x, oy + y), "MX": (ox + x, oy + h - y), "R180": (ox + w - x, oy + h - y)}[o]
for q in P["partitions"]:
    t = P["partition_types"][q["type"]]; w, h = t["outline_um"]
    ax.add_patch(Rectangle(q["origin_um"], w, h, fill=False, lw=0.3, ec="0.6"))
    for c in t.get("hard_cores", []):
        s = c["outline_um"]; x0, y0 = c["origin_um"]
        a = tf(q, w, h, x0, y0); b = tf(q, w, h, x0 + s[0], y0 + s[1])
        ax.add_patch(Rectangle((min(a[0], b[0]), min(a[1], b[1])), abs(b[0] - a[0]), abs(b[1] - a[1]), fc="tan", ec="none", alpha=0.5))
    taps = [tp["xy"] for tp in (t.get("clock") or {}).get("taps", [])] or ([t["clock"]["tap_um"]] if t.get("clock", {}).get("tap_um") else [])
    for x, y in taps:
        X, Y = tf(q, w, h, x, y); ax.plot(X, Y, "s", ms=2.5 if not box else 5, mfc="none", mec="green", mew=0.6)
for io in P["die"].get("io", []):
    r = io["rect_um"]; ax.add_patch(Rectangle(r[:2], r[2] - r[0], r[3] - r[1], fc="violet", alpha=0.25, ec="none"))
N = {n["tag"]: n for n in G["nodes"]}
for n in G["nodes"]:
    if n.get("parent"):
        p = N[n["parent"]]["xy"]; ax.plot([p[0], n["xy"][0]], [p[1], n["xy"][1]], "-", c="red", lw=0.6)
        for k in range(1, n["nseg"]):
            ax.plot(p[0] + (n["xy"][0] - p[0]) * k / n["nseg"], p[1] + (n["xy"][1] - p[1]) * k / n["nseg"], "^", c="blue", ms=1.5 if not box else 4)
for n in G["nodes"]:
    if n["kids"]: ax.plot(*n["xy"], "o", c="k", ms=1.5 if not box else 4)
ax.set_aspect("equal")
if box: ax.set_xlim(box[0], box[2]); ax.set_ylim(box[1], box[3])
else: ax.set_xlim(0, P["die"]["outline_um"][0]); ax.set_ylim(0, P["die"]["outline_um"][1])
ax.set_title("s81_head INFRA-FIRST-HEAD-2: plan B entries (green) + delay-balanced grid tree (red legs, blue reps, black nodes); tan = hard cores, violet = PHY", fontsize=8)
fig.savefig(out, bbox_inches="tight"); print(out)
