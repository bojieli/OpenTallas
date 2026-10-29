#!/usr/bin/env python3
"""render hub-local region around GQ q1 / ring_ag q1 (old + candidate) per hub type; usage: render_slot.py DIE_PLAN OUT_PNG"""
import json, sys
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
P = json.load(open(sys.argv[1]))
C = {"q_hub_nw": [(4527.36, 2626.56)], "q_hub_ne": [(4544.64, 2540.16), (4527.36, 2626.56)]}
fig, axs = plt.subplots(1, 2, figsize=(16, 7))
for ax, tn in zip(axs, ("q_hub_nw", "q_hub_ne")):
    t = P["partition_types"][tn]
    for h in t["hard_cores"]:
        (x, y), (w, hh) = h["origin_um"], h["outline_um"]
        if x > 6200 or x + w < 3800 or y > 3300 or y + hh < 1900: continue
        col = "tab:orange" if "hcollgi_Q__q1" in h["inst"] else ("tab:red" if "ring_ag__q1" in h["inst"] else "lightgrey")
        ax.add_patch(Rectangle((x, y), w, hh, fc=col, ec="k", alpha=.6)); ax.text(x + 3, y + hh / 2, h["inst"].replace("u_", ""), fontsize=6)
    for s in t["internal_stations"]:
        for (x, y) in s["regs_um"]:
            if 3800 < x < 6200 and 1900 < y < 3300: ax.plot(x, y, ".", ms=2, c="tab:blue" if "bus:" not in str(s["conn"]) else "tab:purple")
    for i, (x, y) in enumerate(C[tn]):
        ax.add_patch(Rectangle((x, y), 233.28, 233.28, fill=False, ec="green" if i == 0 else "magenta", lw=2, ls="--"))
    ax.set_xlim(3800, 6200); ax.set_ylim(1900, 3300); ax.set_aspect("equal")
    ax.set_title(f"{tn}: orange GQ q1, red ring_ag q1 (old), dashed = candidate slot(s); dots = planned station regs (purple=bus)", fontsize=8)
plt.tight_layout(); plt.savefig(sys.argv[2], dpi=110)
