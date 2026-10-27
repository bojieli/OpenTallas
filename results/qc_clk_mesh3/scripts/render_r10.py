#!/usr/bin/env python3
"""r10 render: per related seam pair STA uncertainty (pair_unc.json sta_unc_ps, FF) as coloured segments between the
two partition entry taps, legal mesh3 feed vs R9 feed, + nominal entry arrival map.  render_r10.py R2 LEGAL_DIR R9_DIR OUT.png"""
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.collections import LineCollection  # noqa: E402

r2, dl, dr, out = sys.argv[1:5]
rec = json.loads(Path(r2).read_text())
tap = {t["part"]: t["entry"] for t in rec["taps"]}
fig, axs = plt.subplots(2, 2, figsize=(18, 15))
for col, (name, d) in enumerate((("mesh3 top tree, LEGAL cells (r10)", dl), ("R9 16-leaf H-tree feed, LEGAL cells (r10)", dr))):
    pu = json.loads((Path(d) / "sta_in/pair_unc.json").read_text())
    segs = [[tap[r["a"]], tap[r["b"]]] for r in pu["rows"]]
    v = [r["FF"]["sta_unc_ps"] + abs(r["FF"]["nominal_dt_ps"]) for r in pu["rows"]]
    ax = axs[0][col]
    lc = LineCollection(segs, array=v, cmap="viridis", linewidths=2.2, norm=matplotlib.colors.Normalize(0, 260))
    ax.add_collection(lc)
    fig.colorbar(lc, ax=ax, shrink=0.7, label="FF pair clock damage = |nominal dt| + MC var + AOCV (ps)")
    ax.set_xlim(0, 31216)
    ax.set_ylim(0, 26266)
    ax.set_aspect("equal")
    w = max(range(len(v)), key=lambda i: v[i])
    ax.plot(*zip(*segs[w]), "-", c="red", lw=5)
    ax.set_title(f"{name}\n{len(segs)} seam pairs, FF max {max(v):.1f} ps (red), UNCHECKED", fontsize=10)
    nom = json.loads((Path(d) / "die_FF.json").read_text())["samples"]
    n0 = [s for s in nom if s["sample"] == 0][0]["tap_arr_ps"]
    ax = axs[1][col]
    xs = [tap[p][0] for p in n0]
    ys = [tap[p][1] for p in n0]
    m0 = min(n0.values())
    sc = ax.scatter(xs, ys, c=[n0[p] - m0 for p in n0], cmap="plasma", s=28)
    fig.colorbar(sc, ax=ax, shrink=0.7, label="FF nominal entry arrival - min (ps)")
    ax.set_xlim(0, 31216)
    ax.set_ylim(0, 26266)
    ax.set_aspect("equal")
    ax.set_title(f"nominal FF entry arrivals (377 partitions): spread {max(n0.values()) - m0:.1f} ps", fontsize=10)
fig.suptitle("QC-CLK-MESH r10 / INFRA-FIRST-QC-R10: related seam-pair clock damage, legal geometry (units expanded, pin-to-pin)", fontsize=12)
fig.savefig(out, dpi=80, bbox_inches="tight")
