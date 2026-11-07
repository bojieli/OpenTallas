#!/usr/bin/env python3
"""HBM-FORM-TIMING-13 rest_1c visual check: cell density (5-um bins) + named groups overlaid.
    vis_rest1c.py placed.csv OUT.png [W H]"""
import csv
import re
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

rows = list(csv.DictReader(open(sys.argv[1])))
W = float(sys.argv[3]) if len(sys.argv) > 3 else 427.68
H = float(sys.argv[4]) if len(sys.argv) > 4 else 453.6
b = 5.0
nx, ny = int(W / b) + 1, int(H / b) + 1
den = np.zeros((ny, nx))
for r in rows:
    if r["kind"] in ("std", "ff", "buf"):
        x, y, w, h = (float(r[k]) for k in ("x", "y", "w", "h"))
        den[min(ny - 1, int(y / b)), min(nx - 1, int(x / b))] += w * h / (b * b)
groups = [
    ("vm_scalar_data face flops", re.compile(r"^u_bout_u_core_u_vm_scalar_data/q"), "cyan", 6),
    ("p50 pipe regs", re.compile(r"^u_fcore\.u_core_u_vm_scalar_data\\?\["), "lime", 8),
    ("src _0905_/_0913_/_0889_", re.compile(r"ctl_rest\._0(905|913|889)_\\?\["), "red", 10),
    ("_0886_ src", re.compile(r"ctl_rest\._0886_\\?\["), "magenta", 10),
    ("_0888_ dst", re.compile(r"ctl_rest\._0888_\\?\["), "orange", 4),
]
fig, ax = plt.subplots(figsize=(11, 11))
im = ax.imshow(den, origin="lower", extent=(0, nx * b, 0, ny * b), cmap="Greys", vmin=0, vmax=1.0)
fig.colorbar(im, ax=ax, fraction=0.04, label="std-cell fill per 5-um bin")
for lab, rx, c, s in groups:
    pts = [(float(r["x"]), float(r["y"])) for r in rows if rx.search(r["name"])]
    if pts:
        xs, ys = zip(*pts)
        ax.scatter(xs, ys, s=s, c=c, label=f"{lab} ({len(pts)})", edgecolors="none")
hot = (den > 0.7).sum()
ax.set_title(f"{sys.argv[2].split('/')[-1]}: bins >0.7 fill = {hot}")
ax.set_xlim(0, W); ax.set_ylim(0, H); ax.legend(loc="upper left", fontsize=8)
fig.savefig(sys.argv[2], dpi=90, bbox_inches="tight")
print("hot bins", hot, "max", round(float(den.max()), 2))
