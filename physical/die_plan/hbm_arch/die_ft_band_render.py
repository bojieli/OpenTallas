#!/usr/bin/env python3
"""render the die_ft_band rows (NW half): partitions, hard cores (grey), EW bands (orange) / NS stripes (green),
E/W seam port windows (ft = red, other = blue), N/S ft windows (magenta).  usage: render_band.py PLAN.json OUT.png [x0 x1 y0 y1]"""
import json, sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
d = json.load(open(sys.argv[1]))
T = d["partition_types"]; P = {p["name"]: p for p in d["partitions"]}
x0, x1, y0, y1 = (float(v) for v in sys.argv[3:7]) if len(sys.argv) > 6 else (0, 14740, 4300, 8700)
fig, ax = plt.subplots(figsize=(24, 9))
def rect(n):
    p = P[n]; w, h = T[p["type"]]["outline_um"]; return p["origin_um"][0], p["origin_um"][1], w, h
def isft(part, bus):
    return part in P and any(bus in (s["name"] + "_i", s["name"] + "_o") for s in T[P[part]["type"]].get("ft_slots", []) or [])
for n, p in P.items():
    ox, oy, w, h = rect(n)
    if ox > x1 or ox + w < x0 or oy > y1 or oy + h < y0:
        continue
    ax.add_patch(Rectangle((ox, oy), w, h, fill=False, lw=0.8))
    ax.text(ox + 5, oy + h - 60, n, fontsize=7)
    t = T[p["type"]]; my = p.get("orient", "R0") in ("MY", "R180")
    for hc in t.get("hard_cores", []) or []:
        cx, cy = hc["origin_um"]; cw, ch = hc["outline_um"]
        if my: cx = w - cx - cw
        ax.add_patch(Rectangle((ox + cx, oy + cy), cw, ch, color="0.75", lw=0))
    for b in t.get("die_ft_bands", []) or []:
        lo, hi = b["span_um"]
        if b["dir"] == "EW":
            ax.add_patch(Rectangle((ox, oy + lo), w, hi - lo, color="orange", alpha=0.25, lw=0))
        else:
            if my: lo, hi = w - hi, w - lo
            ax.add_patch(Rectangle((ox + lo, oy), hi - lo, h, color="green", alpha=0.18, lw=0))
for pr in d["ports"]:
    s, t_ = pr["src"]["part"], pr["dst"]["part"]
    if s not in P:
        continue
    lo, hi = sorted(pr["window_um"])
    ft = isft(s, pr["src"]["bus"]) or isft(t_, pr["dst"]["bus"])
    ox, oy, w, h = rect(s)
    if pr["face"] in "EW":
        x = ox + w if pr["face"] == "E" else ox
        if y0 <= lo <= y1 and x0 <= x <= x1:
            ax.plot([x, x], [lo, hi], color="red" if ft else "blue", lw=3 if ft else 2, solid_capstyle="butt")
    else:
        y = oy + h if pr["face"] == "N" else oy
        if ft and x0 <= lo <= x1 and y0 <= y <= y1:
            ax.plot([lo, hi], [y, y], color="magenta", lw=3, solid_capstyle="butt")
ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); ax.set_aspect("equal")
ax.set_title(sys.argv[1].split("/")[-2] + ": grey = hard cores, orange = die EW band (M4/M6), green = die NS stripe (M5/M7), "
             "red = ft E/W seam window, blue = bus window, magenta = ft N/S window")
fig.savefig(sys.argv[2], dpi=90, bbox_inches="tight")
