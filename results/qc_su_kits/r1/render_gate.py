#!/usr/bin/env python3
"""render su_kit_gate.py output: macros (+4.32 row halo), sinks, entry island, islands, B/leaf sites, edge paths, repeaters."""
import json
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

outp = sys.argv[-1]
fig, axs = plt.subplots(1, len(sys.argv) - 2, figsize=(7 * (len(sys.argv) - 2), 8.5))
for ax, jf in zip(axs, sys.argv[1:-1]):
    d = json.load(open(jf))
    sx, sy = [], []
    core = None
    for line in open(d["geo"]):
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
            ax.add_patch(Rectangle((r[0] - 4.32, r[1] - 4.32), r[2] - r[0] + 8.64, r[3] - r[1] + 8.64, fc="#f3d6d6", ec="none"))
            ax.add_patch(Rectangle((r[0], r[1]), r[2] - r[0], r[3] - r[1], fc="#bbbbbb", ec="k", lw=0.5))
    ax.add_patch(Rectangle((core[0], core[1]), core[2] - core[0], core[3] - core[1], fill=False, ec="k", lw=0.8))
    ax.scatter(sx, sy, s=0.3, c="#7a9cc6")
    cols = {"L1": "#d62728", "L2": "#2ca02c", "L3": "#9467bd"}
    g4 = d["gates"]["G4_detour_sites"]
    lev = {e["edge"]: e["level"] for e in g4["edges"]}
    for nm, pts in d["edge_paths_um"].items():
        ax.plot([p[0] for p in pts], [p[1] for p in pts], c=cols[lev[nm]], lw=0.8 if lev[nm] != "L3" else 0.5)
    for e in g4["edges"]:
        for r in e.get("repeaters", []):
            ax.plot(*r["xy"], marker="s", ms=4, c="#ff7f0e" if r["legal"] else "k", mec="k", mew=0.4)
    R = d["gates"]["G2_island_rows"]["entry_island"]
    ax.add_patch(Rectangle((R[0], R[1]), R[2] - R[0], R[3] - R[1], fc="#ffd700", ec="k"))
    for i in d["gates"]["G2_island_rows"]["islands"]:
        R = i["rect_um"]
        ax.add_patch(Rectangle((R[0], R[1]), R[2] - R[0], R[3] - R[1], fc="#ff4444" if not i["legal"] else "#ffa500", ec="k"))
        ax.text(R[2] + 1, R[3], i["island"], fontsize=7)
    v = {k: x["verdict"] for k, x in d["gates"].items()}
    ax.set_title(f"{d['name']} k={d['k']}  {d['verdict']}\n{v}\npred(NLDM+off) {d['plan_pred']['TT']} TT", fontsize=7)
    ax.set_aspect("equal")
    ax.set_xlim(0, core[2] + 4.32)
    ax.set_ylim(0, core[3] + 4.32)
fig.tight_layout()
fig.savefig(outp, dpi=130)
