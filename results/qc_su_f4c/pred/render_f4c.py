#!/usr/bin/env python3
"""QC-SU-F4C render: SRAMs + pin-escape windows + CK-column keep-outs, sinks (grey), tree legs as planned L's
(M6 horizontal = blue, M5 vertical = red), islands (squares, labelled with leaf count), B / leaf-driver nodes,
cell size (BUFx8/x10 = small open marker).  usage: render_f4c.py SPEC GEO PLAN.json OUT.png TITLE"""
import json, re, sys
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
spec, geo, pj, out, title = sys.argv[1:6]
t = open(spec).read(); P = json.load(open(pj))
xy = {"root": tuple(map(float, re.search(r"set ot_ms_root \{([\d.]+) ([\d.]+)\}", t).groups()))}; par = {}; cel = {}
for m in re.finditer(r"\{(\S+) (\S+) ([\d.]+) ([\d.]+) (\S+)\}", t.split("set ot_ms_tree {", 1)[1].split("\n}", 1)[0]):
    xy[m.group(1)] = (float(m.group(3)), float(m.group(4))); par[m.group(1)] = m.group(2); cel[m.group(1)] = m.group(5)
for m in re.finditer(r"^\s*\{(\S+) (\S+) \{([\d.]+) ([\d.]+)\}", t.split("set ot_ms_leaves {", 1)[1].split("\n}\nset", 1)[0], re.M):
    xy[m.group(1)] = (float(m.group(3)), float(m.group(4))); par[m.group(1)] = m.group(2)
fig, ax = plt.subplots(figsize=(13, 11.5))
sx, sy = [], []
for l in open(geo):
    f = l.split()
    if f and f[0] == "DIE": ax.add_patch(Rectangle((0, 0), float(f[3]), float(f[4]), fill=False, lw=1.5))
    if f and f[0] == "SINK": sx.append(float(f[1])); sy.append(float(f[2]))
    if f and f[0] == "MACRO":
        r = list(map(float, f[3:7])); ax.add_patch(Rectangle((r[0], r[1]), r[2] - r[0], r[3] - r[1], color="#f3d9a0", alpha=.6))
        ax.text((r[0] + r[2]) / 2, (r[1] + r[3]) / 2, f[1], ha="center", fontsize=8)
ax.scatter(sx, sy, s=1, c="#bbbbbb")
for a, b, a2, d in P["model"]["pin_windows"]: ax.add_patch(Rectangle((a, b), a2 - a, d - b, fill=False, hatch="///", ec="#cc9900", lw=.3))
for a, b, a2, d in P["model"]["ckcol_keepout"]: ax.add_patch(Rectangle((a, b), a2 - a, d - b, color="m", alpha=.4))
LW = {"L1": 1.8, "L2": 1.1, "L3": .6}
for e in P["gates"]["G4_strict"]["edges"]:          # the planned maze path of every tree edge (f4_g4c path_um, every 4th cell)
    pth = e.get("path_um") or []
    for (x0, y0), (x1, y1) in zip(pth, pth[1:]):
        ax.plot([x0, x1], [y0, y1], c="tab:blue" if abs(x1 - x0) >= abs(y1 - y0) else "tab:red", lw=LW[e["level"]])
for n, (x, y) in xy.items():
    c = cel.get(n, "BUFx24_ASAP7_75t_R")
    small = c.startswith(("BUFx8", "BUFx10"))
    if re.fullmatch(r"Q\d+", n):
        ax.plot(x, y, "s", ms=9, mfc="none" if small else "k", mec="k"); ax.text(x + 2, y + 2, n, fontsize=9, weight="bold")
    elif re.fullmatch(r"Q\d+B\d+", n): ax.plot(x, y, "D", ms=5, mfc="none" if small else "g", mec="g")
    elif n == "root": ax.plot(x, y, "*", ms=16, c="r")
    elif "_r" in n: ax.plot(x, y, "o", ms=3, mfc="none" if small else "tab:purple", mec="tab:purple")
    else: ax.plot(x, y, "^", ms=3, c="tab:orange")
for g in P["gates"]["G2_island_rows"]["islands"]:
    r = g["rect_um"]; ax.add_patch(Rectangle((r[0], r[1]), r[2] - r[0], r[3] - r[1], fill=False, ec="k", lw=1.2))
ax.set_aspect("equal"); ax.set_title(title, fontsize=10); ax.set_xlim(-2, 253); ax.set_ylim(-2, 218)
fig.savefig(out, dpi=110, bbox_inches="tight")
