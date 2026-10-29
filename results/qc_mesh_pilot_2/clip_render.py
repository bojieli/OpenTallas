#!/usr/bin/env python3
"""QC-MESH-PILOT-2 render of the clip-routed region: partition outline, A0 hard cores, mesh straps, every DRT wire of
the tree nets (n_*) from the merged drt.def (full DEF path parser: via chains switch layer), clip rects, cells, DRC
markers (design = red X, clip-harness = grey x).  usage: clip_render.py TRIAL_DIR(pilot.json) MERGE_DIR OUT.png [CLIPROOT]"""
import json
import re
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt   # noqa: E402
from matplotlib.patches import Rectangle   # noqa: E402

T, M, out = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
R = Path(sys.argv[4]) if len(sys.argv) > 4 else None
J = json.load(open(T / "pilot.json"))
g, cells = J["geom"], J["cells"]


def segments(txt):
    """yield (net, layer, x0, y0, x1, y1) for every routed wire of every net in a DEF NETS section."""
    sec = txt[txt.index("\nNETS "):txt.index("END NETS")]
    for blk in re.split(r"\n\s*- ", sec)[1:]:
        net = blk.split()[0]
        toks = re.findall(r"\(|\)|[^\s()]+", blk)
        i, lay, pt = 0, None, None
        while i < len(toks):
            t = toks[i]
            if t in ("ROUTED", "NEW", "FIXED", "COVER"):
                lay, pt = toks[i + 1], None
                i += 2
                continue
            if t == "(" and lay:
                x, y = toks[i + 1], toks[i + 2]
                j = toks.index(")", i)
                nx = pt[0] if x == "*" else int(x) / 1000
                ny = pt[1] if y == "*" else int(y) / 1000
                if pt and (nx, ny) != pt:
                    yield net, lay, pt[0], pt[1], nx, ny
                pt = (nx, ny)
                i = j + 1
                continue
            m = re.match(r"VIA(\d)(\d)$", t)
            if m and lay:
                a, b = f"M{m.group(1)}", f"M{m.group(2)}"
                lay = b if lay == a else a
            i += 1


fig, ax = plt.subplots(figsize=(7, 13))
ax.add_patch(Rectangle((0, 0), g["W"], g["H"], fill=False, lw=1.5, ec="k"))
for c in g["cores"]:
    r = c["rect"]
    ax.add_patch(Rectangle((r[0], r[1]), r[2] - r[0], r[3] - r[1], fc="#dddddd", ec="#888888"))
    ax.text((r[0] + r[2]) / 2, (r[1] + r[3]) / 2, c["inst"] + "\n(A0 hard core)", ha="center", va="center", fontsize=8, color="#555")
if R:
    for d in sorted(R.iterdir()):
        if (d / "clip.json").exists():
            r = json.load(open(d / "clip.json"))["rect"]
            ax.add_patch(Rectangle((r[0], r[1]), r[2] - r[0], r[3] - r[1], fill=False, ls="--", lw=0.6, ec="#8c564b"))
y0, y1 = g["y_span"]
x0, x1 = g["x_span"]
for x in g["vx"]:
    ax.plot([x, x], [y0, y1], color="#d62728", lw=2.2, alpha=0.35)
for y in g["hy"]:
    ax.plot([x0, x1], [y, y], color="#ff7f0e", lw=2.2, alpha=0.35)
col = {"M8": "#1f77b4", "M9": "#2ca02c"}
wl = {}
for net, L, xa, ya, xb, yb in segments((M / "drt.def").read_text()):
    if not net.startswith("n_"):
        continue
    wl[L] = wl.get(L, 0) + abs(xb - xa) + abs(yb - ya)
    ax.plot([xa, xb], [ya, yb], color=col.get(L, "#9467bd"), lw=1.0)
for n, c in cells.items():
    st = ("s", 4, "#d62728") if n.startswith("M") else ("^", 6, "#9467bd") if n.startswith("L_clk_c") else \
        ("o", 3, "k") if n.startswith("L_") else ("D", 4, "#1f77b4")
    ax.plot(c["x"], c["y"], st[0], ms=st[1], color=st[2])
S = json.load(open(M / "drc_summary.json"))
nd = nh = 0
for clip, v in S["clips"].items():
    for mk in v.get("markers", []):
        ax.plot(*mk["xy"], "x", ms=9, mew=2, color="red"); nd += 1
for ln in (M / "drc.rpt").read_text().split("violation type: ")[1:]:
    nh += 1
ax.set_xlim(-20, g["W"] + 20); ax.set_ylim(-20, g["H"] + 20); ax.set_aspect("equal")
ax.set_title(f"{g['part']} mesh pilot, DRT by clips (dashed): tree wires M8 blue / M9 green / M1-M7 stacks purple\n"
             f"mesh straps faint red (M9) / orange (M8); drivers red squares, glue taps dots, A0 core taps triangles\n"
             f"tree DRT wire um { {k: round(v) for k, v in sorted(wl.items())} }; DRC markers {nh} (design {S['total']['design']}, red X)",
             fontsize=7)
fig.savefig(out, dpi=110, bbox_inches="tight")
print("render", out, {k: round(v, 1) for k, v in wl.items()}, S["total"])
