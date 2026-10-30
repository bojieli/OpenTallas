"""DIE-QC-39 A0: render a planned slice (same style as gen_a0_tree21 --png): macro+halo boxes, tree legs coloured by
depth (legs over the 60 um window thick red), gates (blue), registers sinks not drawn.  python3 render_plan.py slice freeze lefdir png title"""
import json, sys, re, collections
from pathlib import Path
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
sl, fr, ld, png, title = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5]
ct = json.load(open(sl))["core_tree"]; fr = json.load(open(fr))
HALO = (4.32, 4.32)
fig, ax = plt.subplots(figsize=(7, 16))
for h in fr["hard_children"]:
    t = Path(ld, h["master"] + ".lef").read_text(); w, hh = map(float, re.search(r"SIZE\s+([0-9.]+)\s+BY\s+([0-9.]+)", t).groups())
    x, y = h["at"]; ax.add_patch(plt.Rectangle((x - HALO[0], y - HALO[1]), w + 2 * HALO[0], hh + 2 * HALO[1], fc="#ddd", ec="#888", lw=0.5))
xy = {n["name"]: n["xy_um"] for n in ct["nodes"]}; xy.update({g["inst"]: g["xy_um"] for g in ct["gates"]})
par = {n["name"]: n["parent"] for n in ct["nodes"]}; par.update({g["inst"]: g["parent"] for g in ct["gates"]})
dep = {}
def d(n):
    if n == "port:ck": return 0
    if n not in dep: dep[n] = d(par[n]) + 1
    return dep[n]
T = max(d(n) for n in par); over = 0
for n, p in par.items():
    if p == "port:ck": continue
    l = abs(xy[p][0] - xy[n][0]) + abs(xy[p][1] - xy[n][1])
    over += l > 60
    ax.plot([xy[p][0], xy[n][0]], [xy[p][1], xy[n][1]], color="red" if l > 60 else plt.cm.viridis(d(n) / T), lw=1.6 if l > 60 else 0.5)
ax.scatter([g["xy_um"][0] for g in ct["gates"]], [g["xy_um"][1] for g in ct["gates"]], s=14, c="blue", marker="s", zorder=5)
ax.set_xlim(0, 457.92); ax.set_ylim(0, 1157.76); ax.set_aspect("equal")
ax.set_title(f"{title}\ncells={len(ct['nodes'])} legs>60um (red)={over}", fontsize=8)
fig.savefig(png, dpi=90, bbox_inches="tight")
