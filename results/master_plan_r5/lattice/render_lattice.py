import json, sys
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
geo = json.load(open(sys.argv[1])); dtp = json.load(open(sys.argv[2])); out = sys.argv[3]
lat = dtp["lattice"]; nodes = lat["nodes"]; gate = lat["gate"]
fig, ax = plt.subplots(figsize=(16, 13.5), dpi=110)
for p in geo["parts"]:
    ax.add_patch(Rectangle((p[0], p[1]), p[2]-p[0], p[3]-p[1], fill=False, lw=0.3, ec="#bbbbbb"))
for c in geo["cores"]:
    ax.add_patch(Rectangle((c[0], c[1]), c[2]-c[0], c[3]-c[1], fc="#d8cbb4" if c[6] == "qfd_tile_nk_a0c" else "#9fb7d6", ec="none"))
pos = {n["tag"]: n["xy_um"] for n in nodes}
for n in nodes:
    if n["parent"]:
        a, b = pos[n["parent"]], n["xy_um"]
        ax.plot([a[0], b[0]], [a[1], b[1]], color="#c0392b", lw=2.2 - 0.3 * n["depth"], zorder=3)
for n in nodes:
    col = {"new_partition_island": "#1f77b4", "existing_island": "#2ca02c"}.get(n["binding"], "#ff00ff")
    ax.plot(*n["xy_um"], "s", ms=9 if n["leaves"] > 1 else 6, color=col, zorder=5)
    if n["depth"] <= 1:
        ax.annotate(n["tag"], n["xy_um"], xytext=(6, 6), textcoords="offset points", fontsize=8)
reps = gate["leg_repeater_sites"]
ok = [r["xy_um"] for r in reps if r["binding"] == "partition_bay"]
bad = [r["xy_um"] for r in reps if r["binding"] != "partition_bay"]
if ok: ax.plot([p[0] for p in ok], [p[1] for p in ok], ".", ms=4, color="#111111", zorder=4)
if bad: ax.plot([p[0] for p in bad], [p[1] for p in bad], "x", ms=9, color="#ff00ff", zorder=6)
c = gate.get("commensurate") or {}
ax.set_title(f"{dtp['die']} die H-tree lattice {gate['lattice'][0]}x{gate['lattice'][1]} on channel crosses: "
             f"nodes {gate['nodes']} ({gate['bindings']}), leg reps {gate['leg_repeaters']} / in core {gate['leg_repeaters_in_core']}, "
             f"path spread {gate['path_len_um']['spread']} um\n"
             f"x leaves {c.get('x',{}).get('leaves_um')} (repeat {c.get('x',{}).get('repeat_um')})  "
             f"y leaves {c.get('y',{}).get('leaves_um')} (repeat {c.get('y',{}).get('repeat_um')}, root arm bridge)", fontsize=9)
ax.set_xlim(0, max(p[2] for p in geo["parts"])); ax.set_ylim(0, max(p[3] for p in geo["parts"])); ax.set_aspect("equal")
fig.tight_layout(); fig.savefig(out)
# zoom crop around root + one leaf
for name, (x0, y0, w) in dict(zoom_root=(pos["t"][0]-700, pos["t"][1]-3000, 1400), zoom_leaf=(nodes[-1]["xy_um"][0]-500, nodes[-1]["xy_um"][1]-500, 1000)).items():
    ax.set_xlim(x0, x0 + w); ax.set_ylim(y0, y0 + (6000 if name == "zoom_root" else w)); fig.savefig(out.replace(".png", f"_{name}.png"))
