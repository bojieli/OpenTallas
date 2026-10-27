"""R15 render: lanes of one period (local row x-trees + M9 y-tree lanes) and the centre channel; dry-build errors circled."""
import json, sys
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
plan = json.load(open(sys.argv[1])); S = json.load(open(sys.argv[2])); E = json.load(open(sys.argv[3])); out = sys.argv[4]
cs = S["cell_sites"]; nets = S["nets"]
G = {}
for n, v in cs.items():
    G.setdefault("g%d" % v["group"], []).append(v)
ctr = lambda g: (G[g][0]["origin_um"][0] + G[g][0]["w"] / 2, G[g][0]["origin_um"][1] + 0.135)
rows = E["rows"] if isinstance(E, dict) else E
bad = set()
for r in rows:
    n = r["name"][6:] if r["name"].startswith("ckm_w_") else r["name"]
    if n in cs: bad.add("g%d" % cs[n]["group"])
views = [("period 0, bottom local row 0 + y-tree lanes", (2080, 3900, 2330, 3980)),
         ("period 0 y-tree M9 lanes (x 2100-2260)", (2100, 2600, 2260, 13200)),
         ("centre channel YC=13132.8 (x 4000-13000)", (4000, 13080, 13000, 13190)),
         ("period 0 full local row 0", (2100, 3880, 4100, 3990))]
fig, axs = plt.subplots(2, 2, figsize=(18, 12), dpi=100)
for ax, (t, (x0, y0, x1, y1)) in zip(axs.flat, views):
    for p in plan["partitions"]:
        (px, py), (w, h) = p["origin_um"], plan["partition_types"][p["type"]]["outline_um"]
        if px < x1 and px + w > x0 and py < y1 and py + h > y0:
            ax.add_patch(Rectangle((px, py), w, h, fill=False, lw=0.6, ec="#999"))
    k = int(y0 // 8.64)
    while k * 8.64 < y1:
        ax.axhline(k * 8.64, lw=0.3, c="#c33", alpha=0.35); k += 1
    for e in nets:
        p, q = ctr(e["drv"]), ctr(e["load"])
        if min(p[0], q[0]) > x1 or max(p[0], q[0]) < x0 or min(p[1], q[1]) > y1 or max(p[1], q[1]) < y0: continue
        if e["layer"] == "M8":
            ax.plot([p[0], q[0], q[0]], [p[1], p[1], q[1]], lw=1.0, c="#2e8b57")
        else:
            ax.plot([p[0], p[0], q[0]], [p[1], q[1], q[1]], lw=1.0, c="#1f4e9c")
    col = {"top_node": "#d62728", "top_rep": "#555", "col_tap": "#ff7f0e", "chan_node": "#9467bd", "chan_rep": "#8c564b"}
    for g, us in G.items():
        x, y = ctr(g)
        if x0 <= x <= x1 and y0 <= y <= y1:
            ax.scatter([x], [y], s=14, c=col.get(us[0]["kind"], "k"), zorder=3)
            if g in bad: ax.scatter([x], [y], s=90, facecolors="none", edgecolors="m", zorder=4)
    ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); ax.set_title(t, fontsize=9)
fig.suptitle("INFRA-FIRST-QC-R15: per-level 8.64-um VSS lanes (red = M8 VSS stripes 8.64k; green M8 / blue M9 legs; magenta = dry-build plan error) UNCHECKED", fontsize=10)
fig.savefig(out, bbox_inches="tight")
