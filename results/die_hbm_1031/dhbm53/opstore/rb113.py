import json, sys
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
p = json.load(open(sys.argv[1])); t = p["partition_types"]["q_b113"]
W, H = t["outline_um"]
fig, ax = plt.subplots(figsize=(12, 10))
ax.add_patch(Rectangle((0, 0), W, H, fill=False, lw=2))
for b in t.get("die_ft_bands") or []:
    a, c = b["span_um"]
    if b["dir"] == "EW": ax.add_patch(Rectangle((0, a), W, c - a, fc="#ffe0a0", alpha=.4))
    else: ax.add_patch(Rectangle((a, 0), c - a, H, fc="#a0ffa0", alpha=.4))
for h in t["hard_cores"]:
    x, y = h["origin_um"]; w, hh = h["outline_um"]
    ax.add_patch(Rectangle((x, y), w, hh, fc="#7fa7d9", ec="k", alpha=.7))
    ax.text(x + w / 2, y + hh / 2, h["module"].split("__")[-1] + "\n" + f"{w}x{hh}", ha="center", fontsize=8)
for s in t.get("internal_stations") or []:
    for r in s.get("regs_um", []): ax.plot(*r, "r.", ms=3)
for s in t.get("ft_slots") or []:
    for r in s.get("regs_um", []): ax.plot(*r, "m^", ms=4)
for b in t["buses"] if isinstance(t["buses"], list) else []:
    pass
ax.set_xlim(-20, W + 20); ax.set_ylim(-20, H + 20); ax.set_aspect("equal"); ax.grid(alpha=.3)
ax.set_title("q_b113 d44n hard cores (blue), internal stations (red), ft regs (magenta), die ft bands")
fig.savefig(sys.argv[2], dpi=80, bbox_inches="tight")
