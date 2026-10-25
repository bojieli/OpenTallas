#!/usr/bin/env python3
"""Render the QC die with every partition coloured by its worst actual-bit ft leg (qc_hop_audit.py output).
    python3 qc_hop_render.py REPO PLAN.json HOPS.json OUT.png"""
import json
import sys
from pathlib import Path

repo, plan, hops, out = Path(sys.argv[1]), sys.argv[2], sys.argv[3], sys.argv[4]
sys.path.insert(0, str(repo / "tools" / "die_plan"))
import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402
import schema as S  # noqa: E402

P = S.Plan(json.loads(Path(plan).read_text()))
H = json.loads(Path(hops).read_text())["bit_legs"]["worst"]
worst = {}
nbad = {}
for r in H:
    worst[r["type"]] = max(worst.get(r["type"], 0), r["worst_leg_um"])
    nbad[r["type"]] = nbad.get(r["type"], 0) + r["legs_over_405"]
fig, ax = plt.subplots(figsize=(16, 13))
cm = plt.get_cmap("autumn_r")
for n, p in P.parts.items():
    x0, y0, x1, y1 = P.rect(n)
    ox, oy, w, h = x0, y0, x1 - x0, y1 - y0
    wl = worst.get(p["type"], 0)
    if wl > 405:
        fc = cm(min(1.0, (wl - 405) / 100))
    else:
        fc = "#d8e8d8"
    ax.add_patch(Rectangle((ox, oy), w, h, fc=fc, ec="0.4", lw=0.3))
    if wl > 405 and w > 600:
        ax.text(ox + w / 2, oy + h / 2, f"{p['type']}\n{wl:.0f}", ha="center", va="center", fontsize=5)
ax.set_xlim(0, P.W)
ax.set_ylim(0, P.H)
ax.set_aspect("equal")
sm = plt.cm.ScalarMappable(cmap=cm, norm=plt.Normalize(405, 505))
fig.colorbar(sm, ax=ax, shrink=0.6, label="worst actual-bit ft leg (um), green = <= 405")
ax.set_title(f"{P.name}: partitions with ft bit legs > 405 um (decision 12) -- {len(worst)} types, "
             f"{sum(nbad.values())} type-level legs")
fig.savefig(out, dpi=110, bbox_inches="tight")
print(out)
