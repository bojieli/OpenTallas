"""R17 render (UNCHECKED): (A) whole 43.2-delta die top tree d43b; (B) centre channel x-tree on its 5 VSS lanes;
(C,D) two cbx_q10 instances (the R16 65/66 type) in their own frames, R16f (grey x) vs R17 d43b (dots)."""
import json, sys
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
sys.path.insert(0, sys.argv[0].rsplit("/", 1)[0])
plan_p, s17, s16, oplan_p, out = sys.argv[1:6]
P = json.load(open(plan_p)); P0 = json.load(open(oplan_p))
def load(s):
    S = json.load(open(s)); G = {}
    for n, v in S["cell_sites"].items(): G.setdefault("g%d" % v["group"], []).append(v)
    return S["nets"], G
ctr = lambda G, g: (G[g][0]["origin_um"][0] + G[g][0]["w"] / 2, G[g][0]["origin_um"][1] + 0.135)
def parts(ax, P, x0, y0, x1, y1, cores=True):
    for p in P["partitions"]:
        (px, py), (w, h) = p["origin_um"], P["partition_types"][p["type"]]["outline_um"]
        if px < x1 and px + w > x0 and py < y1 and py + h > y0:
            ax.add_patch(Rectangle((px, py), w, h, fill=False, lw=0.6, ec="#777"))
            if cores:
                o = p.get("orient", "R0")
                for c in P["partition_types"][p["type"]].get("hard_cores", []):
                    (cx, cy), (cw, ch) = c["origin_um"], c["outline_um"]
                    if o in ("MX", "R180"): cy = h - cy - ch
                    if o in ("MY", "R180"): cx = w - cx - cw
                    ax.add_patch(Rectangle((px + cx, py + cy), cw, ch, fc="#f2d7b6", ec="#c08040", lw=0.4, alpha=0.6))
col = {"top_node": "#d62728", "top_rep": "#555", "col_tap": "#ff7f0e", "chan_node": "#9467bd", "chan_rep": "#8c564b"}
def tree(ax, nets, G, w, s=14, mk="o", dots=True):
    x0, y0, x1, y1 = w
    for e in nets:
        p, q = ctr(G, e["drv"]), ctr(G, e["load"])
        if min(p[0], q[0]) > x1 or max(p[0], q[0]) < x0 or min(p[1], q[1]) > y1 or max(p[1], q[1]) < y0: continue
        if e["layer"] == "M8": ax.plot([p[0], q[0], q[0]], [p[1], p[1], q[1]], lw=0.8, c="#2e8b57")
        else: ax.plot([p[0], p[0], q[0]], [p[1], q[1], q[1]], lw=0.8, c="#1f4e9c")
    if dots:
        for g, us in G.items():
            x, y = ctr(G, g)
            if x0 <= x <= x1 and y0 <= y <= y1: ax.scatter([x], [y], s=s, c=col.get(us[0]["kind"], "k"), marker=mk, zorder=3)
def vss(ax, y0, y1):
    k = int(y0 // 8.64)
    while k * 8.64 < y1: ax.axhline(k * 8.64, lw=0.3, c="#c33", alpha=0.35); k += 1
N17, G17 = load(s17); N16, G16 = load(s16)
fig, axs = plt.subplots(2, 2, figsize=(18, 13), dpi=100)
W, H = P["die"]["outline_um"] if "outline_um" in P["die"] else (31216.32, 26308.8)
ax = axs[0, 0]; w = (0, 0, W, H); parts(ax, P, *w, cores=False); tree(ax, N17, G17, w, s=3)
for c in P["die"].get("channels", []):
    if c.get("clock_channel") and "rect_um" in c:
        x0, y0, x1, y1 = c["rect_um"]; ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fc="#1f77b4", alpha=0.5))
ax.set_xlim(0, W); ax.set_ylim(0, H); ax.set_aspect("equal"); ax.set_title(f"d43b 43.2-delta die {W:.0f}x{H:.1f} um: top tree (blue band = clock channel)", fontsize=9)
ax = axs[0, 1]; ch = [c for c in P["die"]["channels"] if c.get("clock_channel")][0]; x0, y0, x1, y1 = ch["rect_um"]
w = (x0 - 50, y0 - 25, x0 + 5200, y1 + 25); parts(ax, P, *w, cores=False); vss(ax, w[1], w[3])
ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fc="#bfe3ff", ec="#1f77b4", alpha=0.5)); tree(ax, N17, G17, w, s=18)
ax.set_xlim(w[0], w[2]); ax.set_ylim(w[1], w[3]); ax.set_title(f"centre channel {ch['rect_um']}: channel x-tree on its VSS lanes (purple node, brown rep)", fontsize=9)
inst = [p for p in P["partitions"] if p["type"] == "cbx_q10"]
inst0 = {p["name"]: p for p in P0["partitions"]}
for ax, p in zip(axs[1], inst[:2]):
    (px, py), (pw, ph) = p["origin_um"], P["partition_types"]["cbx_q10"]["outline_um"]
    w = (px - 20, py - 20, px + pw + 20, py + ph + 20); parts(ax, P, *w); tree(ax, N17, G17, w, s=22)
    q = inst0[p["name"]]; dx, dy = px - q["origin_um"][0], py - q["origin_um"][1]
    for g in G16:
        x, y = ctr(G16, g); x += dx; y += dy
        if w[0] <= x <= w[2] and w[1] <= y <= w[3]: ax.scatter([x], [y], s=40, c="#999", marker="x", zorder=4)
    ax.set_xlim(w[0], w[2]); ax.set_ylim(w[1], w[3]); ax.set_aspect("equal")
    ax.set_title(f"{p['name']} (cbx_q10, {p.get('orient','R0')}): R17 dots vs R16f grey x (shifted to delta die)", fontsize=9)
fig.suptitle("INFRA-FIRST-QC-R17 d43b (UNCHECKED render): green M8 / blue M9 legs; red top node, grey rep, orange col tap; tan hard cores", fontsize=10)
fig.savefig(out, bbox_inches="tight"); print(out, len(inst))
