#!/usr/bin/env python3
"""QC-MESH-PILOT-1 render: partition outline, A0 hard cores, mesh straps (M8/M9), detail-routed pre-mesh tree wires
(from drt.def, per layer), tree cells / mesh drivers / tap loads.  usage: pilot_render.py TRIAL_DIR OUT.png"""
import json
import re
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt   # noqa: E402
from matplotlib.patches import Rectangle   # noqa: E402

T = Path(sys.argv[1])
J = json.load(open(T / "pilot.json"))
g, cells = J["geom"], J["cells"]
fig, ax = plt.subplots(figsize=(7, 13))
ax.add_patch(Rectangle((0, 0), g["W"], g["H"], fill=False, lw=1.5, ec="k"))
for c in g["cores"]:
    r = c["rect"]
    ax.add_patch(Rectangle((r[0], r[1]), r[2] - r[0], r[3] - r[1], fc="#dddddd", ec="#888888"))
    ax.text((r[0] + r[2]) / 2, (r[1] + r[3]) / 2, c["inst"] + "\n(A0 hard core)", ha="center", va="center", fontsize=8, color="#555")
y0, y1 = g["y_span"]
x0, x1 = g["x_span"]
for x in g["vx"]:
    ax.plot([x, x], [y0, y1], color="#d62728", lw=2.2, alpha=0.6, label=None)
for y in g["hy"]:
    ax.plot([x0, x1], [y, y], color="#ff7f0e", lw=2.2, alpha=0.6)
col = {"M8": "#1f77b4", "M9": "#2ca02c"}
nseg = {}
dfile = T / "drt.def"
if dfile.exists():
    txt = dfile.read_text()
    nets = txt[txt.index("\nNETS "):txt.index("END NETS")]
    for blk in nets.split("\n- ")[1:]:
        name = blk.split()[0]
        if not name.startswith("n_"):
            continue
        for m in re.finditer(r"(?:ROUTED|NEW) (M\d)\s+(?:\S+\s+)?\(\s*(\d+)\s+(\d+)[^)]*\)\s*\(\s*(\*|\d+)\s+(\*|\d+)[^)]*\)", blk):
            L = m.group(1)
            xa, ya = int(m.group(2)) / 1000, int(m.group(3)) / 1000
            xb = xa if m.group(4) == "*" else int(m.group(4)) / 1000
            yb = ya if m.group(5) == "*" else int(m.group(5)) / 1000
            nseg[L] = nseg.get(L, 0) + 1
            ax.plot([xa, xb], [ya, yb], color=col.get(L, "#9467bd"), lw=0.9)
elif (T / "route.guide").exists():      # GRT stage: the M8/M9 guide boxes of the tree nets (centre lines)
    cur = None
    for ln in open(T / "route.guide"):
        f = ln.split()
        if len(f) == 1 and f[0] not in ("(", ")"):
            cur = f[0]; continue
        if len(f) == 5 and f[4] in ("M8", "M9") and cur and cur.startswith("n_"):
            xa, ya, xb, yb = (int(v) / 1000 for v in f[:4])
            if f[4] == "M8" and xb - xa > 1.0:
                ax.plot([xa, xb], [(ya + yb) / 2] * 2, color=col["M8"], lw=0.9); nseg["M8"] = nseg.get("M8", 0) + 1
            elif f[4] == "M9" and yb - ya > 1.0:
                ax.plot([(xa + xb) / 2] * 2, [ya, yb], color=col["M9"], lw=0.9); nseg["M9"] = nseg.get("M9", 0) + 1
for n, c in cells.items():
    if n.startswith("M"):
        ax.plot(c["x"], c["y"], "s", ms=4, color="#d62728")
    elif n.startswith("L_clk_c"):
        ax.plot(c["x"], c["y"], "^", ms=6, color="#9467bd")
    elif n.startswith("L_"):
        ax.plot(c["x"], c["y"], "o", ms=3, color="k")
    else:
        ax.plot(c["x"], c["y"], "D", ms=4, color="#1f77b4")
ax.set_xlim(-20, g["W"] + 20); ax.set_ylim(-20, g["H"] + 20); ax.set_aspect("equal")
ax.set_title(f"{g['part']} mesh pilot: M9 straps (red) / M8 straps (orange); DRT tree M8 blue / M9 green / other purple\n"
             f"drivers red squares (32), glue taps black dots (28), A0 core taps purple triangles, tree cells blue diamonds\n"
             f"{'DRT drt.def' if dfile.exists() else 'GRT route.guide'} segs {nseg}", fontsize=7)
fig.savefig(sys.argv[2], dpi=110, bbox_inches="tight")
print("render", sys.argv[2], nseg)
