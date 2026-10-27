#!/usr/bin/env python3
"""HEAD-CORE-R14: render in-core plan trees (mscts_h spec tcl: ot_ms_root + ot_ms_tree {name parent x y cell}) over the
placed clock sinks of a geo (dump_geo format), one panel per spec, edges as L routes (x first), level-1 legs bold.
usage: head_plan_tree_render.py GEO OUT.png TITLE SPEC[:LABEL] [SPEC[:LABEL] ...]"""
import re
import sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle


def read_spec(p):
    t = open(p).read()
    m = re.search(r"set ot_ms_root \{([\d.]+) ([\d.]+)\}", t)
    root = (float(m.group(1)), float(m.group(2)))
    blk = t[t.index("set ot_ms_tree {"):]
    blk = blk[:blk.index("\n}")]
    nodes = {"root": (root, None, "root")}
    for name, par, x, y, cell in re.findall(r"\{(\S+) (\S+) ([\d.]+) ([\d.]+) (\S+)\}", blk):
        nodes[name] = ((float(x), float(y)), par, cell)
    return root, nodes


def level(nodes, n):
    d = 0
    while nodes[n][1] is not None:
        n = nodes[n][1]
        d += 1
    return d


geo, out, title = sys.argv[1:4]
specs = sys.argv[4:]
S, M, die = [], [], None
for ln in open(geo):
    f = ln.split()
    if f and f[0] == "SINK":
        S.append((float(f[1]), float(f[2])))
    elif f and f[0] == "MACRO":
        M.append(tuple(map(float, f[3:7])))
    elif f and f[0] == "DIE":
        die = tuple(map(float, f[1:5]))
fig, axs = plt.subplots(1, len(specs), figsize=(7.5 * len(specs), 7.8))
axs = axs if len(specs) > 1 else [axs]
for ax, sp in zip(axs, specs):
    path, _, lab = sp.partition(":")
    root, nodes = read_spec(path)
    ax.scatter([s[0] for s in S], [s[1] for s in S], s=0.15, c="#bbbbbb", lw=0)
    for x0, y0, x1, y1 in M:
        ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fc="#f3d9a4", ec="#a07020", alpha=0.6))
    col = {1: "#d62728", 2: "#1f77b4", 3: "#2ca02c", 4: "#9467bd", 5: "#8c564b"}
    l1 = []
    for n, (xy, par, cell) in nodes.items():
        if par is None:
            continue
        pxy = nodes[par][0]
        lv = level(nodes, n)
        c = col.get(lv, "#555555")
        lw = 2.6 if lv == 1 else (1.6 if lv == 2 else 0.6)
        ax.plot([pxy[0], xy[0], xy[0]], [pxy[1], pxy[1], xy[1]], c=c, lw=lw)
        ax.plot([xy[0]], [xy[1]], "o", ms=3 if lv <= 2 else 1.5, c=c)
        if lv == 1:
            l1.append(abs(xy[0] - pxy[0]) + abs(xy[1] - pxy[1]))
            if cell != "BUFx24_ASAP7_75t_R":
                ax.annotate(cell.split("_")[0], xy, fontsize=8, color=c)
    ax.plot([root[0]], [root[1]], "k*", ms=14)
    ax.set_xlim(die[0], die[2]); ax.set_ylim(die[1], die[3]); ax.set_aspect("equal")
    ax.set_title(f"{lab or path}\nroot {root[0]:.2f},{root[1]:.2f}; nodes {len(nodes) - 1}; root legs (um) "
                 + ",".join(f"{v:.0f}" for v in l1), fontsize=9)
fig.suptitle(title, fontsize=11)
fig.tight_layout()
fig.savefig(out, dpi=110)
print("wrote", out)
