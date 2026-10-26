#!/usr/bin/env python3
"""QC-SU-F4-2 render of the G4-strict as-built plan (f4_g4ab.py json + geo). usage: render_g4.py OUT.png NAME1 GEO1 JSON1 [NAME2 GEO2 JSON2 ...]"""
import json
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

out = sys.argv[1]
items = [sys.argv[i:i + 3] for i in range(2, len(sys.argv), 3)]
fig, axs = plt.subplots(1, len(items), figsize=(11 * len(items), 10))
axs = axs if len(items) > 1 else [axs]
for ax, (name, geo, js) in zip(axs, items):
    d = json.load(open(js))
    sx, sy = [], []
    for line in open(geo):
        f = line.split()
        if not f:
            continue
        if f[0] == "CORE":
            core = list(map(float, f[1:5]))
        if f[0] == "SINK":
            sx.append(float(f[1]))
            sy.append(float(f[2]))
        if f[0] == "MACRO":
            r = list(map(float, f[3:7]))
            ax.add_patch(Rectangle((r[0] - 4.32, r[1] - 4.32), r[2] - r[0] + 8.64, r[3] - r[1] + 8.64, color="#f4cccc", zorder=0))
            ax.add_patch(Rectangle((r[0], r[1]), r[2] - r[0], r[3] - r[1], color="#bbbbbb", zorder=1))
            ax.plot([float(f[8])], [float(f[9])], "k^", ms=9, zorder=6)
    ax.add_patch(Rectangle((core[0], core[1]), core[2] - core[0], core[3] - core[1], fill=False, lw=1))
    for a, b, c, e in d["model"]["pin_windows"]:
        ax.add_patch(Rectangle((a, b), c - a, e - b, fill=False, hatch="//", ec="#cc8800", lw=0.5, zorder=2))
    for a, b, c, e in d["model"]["ckcol_keepout"]:
        ax.add_patch(Rectangle((a, b), c - a, e - b, fill=False, ec="red", lw=1.5, zorder=5))
    ax.scatter(sx, sy, s=0.3, c="#6688cc", zorder=2)
    col = {"L1": "red", "L2": "green", "L3": "#9966cc"}
    lw = {"L1": 2.0, "L2": 1.2, "L3": 0.6}
    for e in d["gates"]["G4_strict"]["edges"]:
        p = e.get("path_um", [])
        if p:
            ax.plot([q[0] for q in p], [q[1] for q in p], color=col[e["level"]], lw=lw[e["level"]], zorder=3)
        for cc in e.get("cells", []):
            ax.plot([cc[0]], [cc[1]], marker="*" if e.get("detour") else "s", color="black" if e["level"] == "L1" else col[e["level"]],
                    ms=10 if e["level"] == "L1" else 4, zorder=7)
    for i in d["gates"]["G2_island_rows"]["islands"]:
        R = i["rect_um"]
        ax.add_patch(Rectangle((R[0], R[1]), R[2] - R[0], R[3] - R[1], color="orange", ec="k", zorder=6))
        ax.text(R[2] + 1, R[3], i["island"], fontsize=9, zorder=8)
    P = d["pred"]
    ax.set_title(f"{name} G4-strict {d['verdict']} k={d['k']} policies={d['model']['policies']}\n"
                 f"as-built TT avg {P['TT']['avg']['mean']} w{P['TT']['avg']['window']} (incl SRAM w{P['TT']['avg']['window_incl_sram']}) | "
                 f"FF early {P['FF']['early']['mean']} / late {P['FF']['late']['mean']} w{P['FF']['early']['window']}  trunk "
                 f"{d.get('entry_trunk', {}).get('cell')} (PLAN MODEL, UNCHECKED)\n"
                 "red=L1 green=L2 violet=L3, * = waypoint cell fixing a detour, hatched = pin-escape band, red box = SRAM CK column keep-out",
                 fontsize=9)
    ax.set_aspect("equal")
    ax.set_xlim(core[0] - 6, core[2] + 6)
    ax.set_ylim(core[1] - 6, core[3] + 6)
fig.tight_layout()
fig.savefig(out, dpi=110)
print(out)
