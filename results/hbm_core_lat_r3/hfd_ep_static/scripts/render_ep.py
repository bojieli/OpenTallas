#!/usr/bin/env python3
"""HBM-CORE-LAT-R3 hfd_ep_static render: outline, SRAM macros, clock sinks (coloured by planned leaf), planned
H-tree (entry -> branch/rep -> leaf drivers), as-placed tree cells (TREE lines), plan pins by layer on the faces.
usage: render_ep.py GEO PLAN_JSON PLAN_TCL PINS_JSON OUT.png [--placed TREE_DUMP] [--title T]"""
import json, sys, re, colorsys
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
geo, pj, spec, pins, out = sys.argv[1:6]
placed = sys.argv[sys.argv.index("--placed") + 1] if "--placed" in sys.argv else None
title = sys.argv[sys.argv.index("--title") + 1] if "--title" in sys.argv else ""
P = json.load(open(pj))
fig, ax = plt.subplots(figsize=(10, 14))
sinkxy = {}
for ln in open(geo):
    f = ln.split()
    if not f: continue
    if f[0] == "DIE": d = list(map(float, f[1:5])); ax.add_patch(Rectangle((d[0], d[1]), d[2]-d[0], d[3]-d[1], fill=False, lw=1.5))
    if f[0] == "CORE": c = list(map(float, f[1:5])); ax.add_patch(Rectangle((c[0], c[1]), c[2]-c[0], c[3]-c[1], fill=False, ls=":", lw=0.6))
    if f[0] == "MACRO":
        x0, y0, x1, y1 = map(float, f[3:7]); ax.add_patch(Rectangle((x0, y0), x1-x0, y1-y0, fc="#c8c8c8", ec="k", lw=0.6))
        ax.plot(float(f[8]), float(f[9]), "s", color="orange", ms=4)
    if f[0] == "SINK": sinkxy[f[4] + "/" + f[5]] = (float(f[1]), float(f[2]))
# sinks by leaf (plan Tcl membership)
txt = open(spec).read()
m = re.search(r"^set ot_ms_leaves \{\n(.*?)^\}", txt, re.S | re.M)
leaves = m.group(1).strip().splitlines() if m else []
for i, ln in enumerate(leaves):
    nm = ln.strip()[1:].split()[0]
    mem = re.findall(r"\{\{([^}]*)\} \{([^}]*)\}\}", ln)
    col = colorsys.hsv_to_rgb((i * 0.618) % 1, 0.75, 0.85)
    xs = [sinkxy[a + "/" + b][0] for a, b in mem if a + "/" + b in sinkxy]
    ys = [sinkxy[a + "/" + b][1] for a, b in mem if a + "/" + b in sinkxy]
    ax.scatter(xs, ys, s=0.6, color=col, lw=0)
pos = {n[0]: n[2] for n in P["nodes"]}
depth = {}
for n in P["nodes"]:
    d, u = 0, n[0]
    par = {q[0]: q[1] for q in P["nodes"]}
    while par[u]: u = par[u]; d += 1
    depth[n[0]] = d
cols = ["red", "magenta", "blue", "green", "teal", "purple", "brown", "olive"]
for nm, par, xy, master, kind in P["nodes"]:
    if par:
        a, b = pos[par], xy
        ax.plot([a[0], a[0], b[0]], [a[1], b[1], b[1]], "-", color=cols[min(depth[nm], 7)], lw=1.4 if kind != "leaf" else 0.5)
    ax.plot(xy[0], xy[1], "o" if kind != "leaf" else ".", color=cols[min(depth[nm], 7)], ms=5 if kind != "leaf" else 3)
ex, ey = P["entry"]; ax.plot(ex, ey, "k*", ms=18, zorder=10)
if placed:
    xs, ys = [], []
    for ln in open(placed):
        f = ln.split()
        if f and f[0] == "TREE": xs.append(float(f[2])); ys.append(float(f[3]))
    ax.plot(xs, ys, "x", color="black", ms=4, mew=0.8, label="placed tree cells (%d)" % len(xs))
lc = {"M4": "#1f77b4", "M5": "#d62728"}
pp = json.load(open(pins))
pp = pp if isinstance(pp, list) else pp.get("pins", [])
for q in pp:
    ax.plot(q["x"], q["y"], "|" if q["layer"] == "M5" else "_", color=lc.get(q["layer"], "k"), ms=3, mew=0.5)
ax.set_aspect("equal"); ax.set_xlim(-5, P.get("outline", [255])[0] + 5 if "outline" in P else 256); ax.set_ylim(-5, 381)
ax.set_title(title, fontsize=9); ax.legend(loc="upper right", fontsize=7) if placed else None
fig.tight_layout(); fig.savefig(out, dpi=110)
print("RENDER", out, "leaves", len(leaves), "sinks_drawn", len(sinkxy))
