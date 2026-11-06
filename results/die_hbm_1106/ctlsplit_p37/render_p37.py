#!/usr/bin/env python3
"""part 37 plan-time GEOM render: q_b113 hard cores, the rest/pipe slots, seam + reset pins, clock taps, station registers.
    render_p37.py PLAN_DIR OUT.png"""
import json, sys
from pathlib import Path
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
d = Path(sys.argv[1]); P = json.loads((d / "die_plan.json").read_text()); T = P["partition_types"]["q_b113"]
fig, axs = plt.subplots(1, 2, figsize=(22, 10), dpi=110)
for ax, zoom in zip(axs, (None, (300, 960, 980, 1500))):
    W, H = T["outline_um"]; ax.add_patch(Rectangle((0, 0), W, H, fill=False, lw=1.5))
    for h in T["hard_cores"] + T["contents"][1:]:
        (x, y), (w, hh) = h["origin_um"], h["outline_um"]
        c = "tab:red" if h.get("inst", "").startswith("u_sfucore_Q_ctl") else "tab:blue"
        ax.add_patch(Rectangle((x, y), w, hh, fill=True, alpha=0.18, color=c)); ax.add_patch(Rectangle((x, y), w, hh, fill=False, lw=0.8, color=c))
        if zoom is None or (zoom[0] < x + w / 2 < zoom[2] and zoom[1] < y + hh / 2 < zoom[3]):
            ax.text(x + w / 2, y + hh / 2, f"{h.get('inst')}\n{h['module'][-28:]}\n{w}x{hh} {h.get('orient', 'R0')}", ha="center", va="center", fontsize=6)
        if h.get("inst", "").startswith("u_sfucore_Q_ctl__"):
            pins = json.loads((d / h["pins_file"]).read_text()); mir = h.get("orient") == "MY"
            for p in pins:
                px = x + (w - p["x"] if mir else p["x"]); py = y + p["y"]
                col = "green" if p["name"].startswith("seam_d") else "purple" if p["name"].startswith("seam_q") else "orange" if p["name"].startswith("rst") else "black" if p["name"] == "clk" else None
                if col:
                    ax.plot(px, py, ".", ms=1.5 if p["name"].startswith("seam") else 5, color=col)
    for tp in T["clock"]["taps"]:
        ax.plot(*tp["xy"], "k+", ms=8)
    for s in T["internal_stations"]:
        for r in s.get("regs_um") or []:
            ax.plot(*r, "s", ms=2, color="gray")
    ax.set_aspect("equal")
    if zoom: ax.set_xlim(zoom[0], zoom[2]); ax.set_ylim(zoom[1], zoom[3]); ax.set_title("zoom: rest (MY) + pipe; green seam_d, purple seam_q, orange rst, + taps, grey station regs")
    else: ax.set_xlim(-20, W + 20); ax.set_ylim(-20, H + 20); ax.set_title("q_b113 part 37 (red = ctl rest + pipe)")
fig.tight_layout(); fig.savefig(sys.argv[2]); print("render", sys.argv[2])
