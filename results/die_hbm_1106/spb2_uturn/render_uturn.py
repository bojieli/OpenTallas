#!/usr/bin/env python3
"""render_uturn.py BASE.json NEW.json OUT.png: q_spb2 plan-time GEOM for the U-turn event (hard cores grey, soft
contents dashed, N-face windows of the two slots, OLD station points red x, NEW per-bit sites (every 3rd) coloured,
other slots' explicit sites light blue, internal-station regs small black dots)."""
import json, sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
A, B = (json.load(open(p)) for p in sys.argv[1:3])
A = A["partition_types"]["q_spb2"] if "partition_types" in A else A
B = B["partition_types"]["q_spb2"] if "partition_types" in B else B
w, h = B["outline_um"]
fig, ax = plt.subplots(1, 1, figsize=(17, 15))
ax.add_patch(Rectangle((0, 0), w, h, fill=False, ec="k", lw=1))
for hc in B["hard_cores"]:
    (x, y), (cw, ch) = hc["origin_um"], hc["outline_um"]
    ax.add_patch(Rectangle((x, y), cw, ch, fc="0.8", ec="0.3")); ax.text(x + 5, y + ch / 2, hc["inst"] + " (OBS M5)", fontsize=9)
for c in B["contents"]:
    if any(c["inst"] == hc["inst"] for hc in B["hard_cores"]):
        continue
    (x, y), (cw, ch) = c["origin_um"], c["outline_um"]
    ax.add_patch(Rectangle((x, y), cw, ch, fill=False, ec="0.4", ls="--")); ax.text(x, y - 8, c["inst"], fontsize=7)
for s in B.get("internal_stations") or []:
    ax.scatter([p[0] for p in s["regs_um"]], [p[1] for p in s["regs_um"]], s=4, c="k")
so = {s["name"]: s for s in A["ft_slots"]}
col = {"L1278x3": "tab:green", "L1280x6": "tab:purple"}
for s in B["ft_slots"]:
    if s["name"] in col:
        c = col[s["name"]]
        for lo, hi in (s["in_window_um"], s["out_window_um"]):
            ax.plot([lo, hi], [h + 6, h + 6], c=c, lw=4)
        r0 = so[s["name"]]["regs_um"]
        ax.plot([p[0] for p in r0[1:]], [p[1] for p in r0[1:]], "rx", ms=9, mew=2)
        for j, st in enumerate(s["bit_sites_um"], 1):
            ax.scatter([p[0] for p in st[::3]], [p[1] for p in st[::3]], s=0.5, c=c)
            q = s["regs_um"][j]; ax.text(q[0] + 4, q[1] + 4, f"{s['name']} s{j}", fontsize=8, color=c)
    elif s.get("bit_sites_um"):
        for st in s["bit_sites_um"]:
            ax.scatter([p[0] for p in st[::5]], [p[1] for p in st[::5]], s=0.3, c="tab:blue", alpha=0.4)
        ax.text(s["regs_um"][1][0] + 5, s["regs_um"][1][1], s["name"], fontsize=7, color="tab:blue")
    else:
        ax.plot([p[0] for p in s["regs_um"]], [p[1] for p in s["regs_um"]], "b.", ms=5)
        ax.text(s["regs_um"][-1][0] + 5, s["regs_um"][-1][1], s["name"], fontsize=7, color="b")
ax.set_xlim(-20, w + 20); ax.set_ylim(-20, h + 30); ax.set_aspect("equal")
ax.set_title("q_spb2 d44v U-turn event: L1278x3 (green) / L1280x6 (purple) new per-bit station sites; red x = old N-edge stations")
fig.tight_layout(); fig.savefig(sys.argv[3], dpi=70); print("wrote", sys.argv[3])
