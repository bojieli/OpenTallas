#!/usr/bin/env python3
"""CORES-KITS/KVX 10-26: post-CTS render of a kv3_pv_pair kit from a tools/autopilot/geom_dump.tcl dump.
    python3 render_cts.py DUMP.tsv TAPS.json OUT.png [TITLE]
Draws macros, std cells (seq / comb / buffers), clock cells (CK* / clock-net buffers), face pins, the regional tap
buffers (ot_pv_tap_*) with their group name and sink count, and the tap -> first-level clock driver wires."""
import json
import sys
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

dump, tapsf, outp = sys.argv[1:4]
title = sys.argv[4] if len(sys.argv) > 4 else ""
C, P, N = {}, {}, []
die = None
for l in open(dump):
    f = l.rstrip("\n").split("\t")
    if f[0] == "D":
        die = list(map(float, f[1:5]))
    elif f[0] == "C":
        C[f[1]] = dict(k=f[2], m=f[3], bb=list(map(float, f[4:8])), n=f[8])
    elif f[0] == "P":
        P[f[1]] = dict(n=f[2], x=float(f[6]), y=float(f[7]))
    elif f[0] == "N" and f[1] == "clock" if len(f) > 1 else False:
        N.append(f)
# clock nets: sig field 'CLOCK'? keep every net whose driver is a K/B cell named ot_pv_tap or a clock cell
clk_cells = set()
for l in open(dump):
    f = l.rstrip("\n").split("\t")
    if f[0] == "N" and f[1].upper() == "CLOCK":
        for t in f[2:]:
            if t.startswith("i"):
                clk_cells.add(t[1:].rstrip("c"))
fig, ax = plt.subplots(figsize=(16, 8.5), dpi=110)
ax.add_patch(Rectangle((die[0], die[1]), die[2] - die[0], die[3] - die[1], fill=False, lw=1))
cols = dict(S="tab:blue", L="0.75", B="tab:green", K="tab:red")
pts = defaultdict(list)
for i, c in C.items():
    x0, y0, x1, y1 = c["bb"]
    if c["k"] == "M":
        ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fc="tan", ec="k", lw=0.6, alpha=0.8))
        ax.text((x0 + x1) / 2, (y0 + y1) / 2, c["n"].replace("\\", "").replace("u_slice.", "").replace(".u_mem", ""), fontsize=6, ha="center")
        continue
    k = c["k"]
    if i in clk_cells and k in "BK" and not c["n"].startswith("ot_pv_tap"):
        k = "K"
    pts[k].append(((x0 + x1) / 2, (y0 + y1) / 2))
for k in ("L", "S", "B", "K"):
    if pts[k]:
        xs, ys = zip(*pts[k])
        ax.scatter(xs, ys, s=0.15 if k != "K" else 3, c=cols[k], lw=0, label=f"{k} {len(xs)}", zorder=2 if k != "K" else 4)
xs = [p["x"] for p in P.values()]; ys = [p["y"] for p in P.values()]
ax.scatter(xs, ys, s=1, c="k", marker="s", zorder=3, label=f"pins {len(xs)}")
taps = json.load(open(tapsf))
for nm, t in taps.items():
    ax.scatter([t["x"]], [t["y"]], s=90, marker="*", c="magenta", ec="k", zorder=6)
    b = t["bbox"]
    ax.add_patch(Rectangle((b[0], b[1]), b[2] - b[0], b[3] - b[1], fill=False, ec="magenta", lw=0.5, ls="--", zorder=5))
    ax.text(t["x"] + 2, t["y"] + 2, f"{t['group']}\n{t['sinks']}", fontsize=7, color="purple", zorder=7)
ax.set_xlim(die[0] - 5, die[2] + 5); ax.set_ylim(die[1] - 5, die[3] + 5); ax.set_aspect("equal")
ax.legend(loc="upper right", fontsize=7, markerscale=8)
ax.set_title(title, fontsize=9)
fig.tight_layout(); fig.savefig(outp)
print("wrote", outp, "clock cells", len(pts["K"]))
