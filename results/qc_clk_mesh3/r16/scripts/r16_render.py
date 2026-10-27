"""R16 render (UNCHECKED): A/B nudged seam row lanes R15 vs R16 --island-edge-sym (dry errors circled); C su row local
x-tree R15 (lanes into su_l0 cores) vs R16 --row-at (cb top band); D 43.2-um centre channel plan delta + crossings."""
import json, sys
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
plan, r15s, r15e, r16s, r16e, r16fs, dplan, out = sys.argv[1:9]
plan = json.load(open(plan)); dplan = json.load(open(dplan))
def load(s, e):
    S = json.load(open(s)); E = json.load(open(e)) if e != "-" else {"rows": []}
    cs = S["cell_sites"]; G = {}
    for n, v in cs.items(): G.setdefault("g%d" % v["group"], []).append(v)
    bad = set()
    for r in E["rows"]:
        n = r["name"][6:] if r["name"].startswith("ckm_w_") else r["name"]
        if n in cs: bad.add("g%d" % cs[n]["group"])
    return S["nets"], G, bad
def parts(ax, P, x0, y0, x1, y1, cores=True):
    for p in P["partitions"]:
        (px, py), (w, h) = p["origin_um"], P["partition_types"][p["type"]]["outline_um"]
        if px < x1 and px + w > x0 and py < y1 and py + h > y0:
            ax.add_patch(Rectangle((px, py), w, h, fill=False, lw=0.8, ec="#777"))
            if cores:
                o = p.get("orient", "R0")
                for c in P["partition_types"][p["type"]].get("hard_cores", []):
                    (cx, cy), (cw, ch) = c["origin_um"], c["outline_um"]
                    if o in ("MX", "R180"): cy = h - cy - ch
                    if o in ("MY", "R180"): cx = w - cx - cw
                    ax.add_patch(Rectangle((px + cx, py + cy), cw, ch, fc="#f2d7b6", ec="#c08040", lw=0.5, alpha=0.6))
def tree(ax, nets, G, bad, x0, y0, x1, y1):
    ctr = lambda g: (G[g][0]["origin_um"][0] + G[g][0]["w"] / 2, G[g][0]["origin_um"][1] + 0.135)
    for e in nets:
        p, q = ctr(e["drv"]), ctr(e["load"])
        if min(p[0], q[0]) > x1 or max(p[0], q[0]) < x0 or min(p[1], q[1]) > y1 or max(p[1], q[1]) < y0: continue
        if e["layer"] == "M8": ax.plot([p[0], q[0], q[0]], [p[1], p[1], q[1]], lw=1.0, c="#2e8b57")
        else: ax.plot([p[0], p[0], q[0]], [p[1], q[1], q[1]], lw=1.0, c="#1f4e9c")
    col = {"top_node": "#d62728", "top_rep": "#555", "col_tap": "#ff7f0e", "chan_node": "#9467bd", "chan_rep": "#8c564b"}
    nb = 0
    for g, us in G.items():
        x, y = ctr(g)
        if x0 <= x <= x1 and y0 <= y <= y1:
            ax.scatter([x], [y], s=16, c=col.get(us[0]["kind"], "k"), zorder=3)
            if g in bad: ax.scatter([x], [y], s=110, facecolors="none", edgecolors="m", lw=1.5, zorder=4); nb += 1
    return nb
def vss(ax, y0, y1):
    k = int(y0 // 8.64)
    while k * 8.64 < y1: ax.axhline(k * 8.64, lw=0.3, c="#c33", alpha=0.35); k += 1
A = load(r15s, r15e); B = load(r16s, r16e); C = load(r16fs, "-")
fig, axs = plt.subplots(2, 2, figsize=(18, 12), dpi=100)
w = (2400, 2600, 3200, 2680)
for ax, (t, d) in zip(axs.flat[:2], (("R15: nudged seam row 2626.56 (lane-0 reps pushed onto lane 1)", A), ("R16 --island-edge-sym: same row, lane 0 kept", B))):
    parts(ax, plan, *w); vss(ax, w[1], w[3]); n = tree(ax, *d, *w)
    ax.set_xlim(w[0], w[2]); ax.set_ylim(w[1], w[3]); ax.set_title(f"{t}; dry errors circled here: {n}", fontsize=9)
w = (3300, 10380, 4150, 10560)
ax = axs.flat[2]; parts(ax, plan, *w); vss(ax, w[1], w[3])
tree(ax, *A, *w); tree(ax, *C, *w)
ax.set_xlim(w[0], w[2]); ax.set_ylim(w[1], w[3])
ax.set_title("su row local x-tree: R15 row 10471.68 (lanes into su_l0 cores, merge 127 um off-centre) + R16 --row-at -> 10445.76 (cb top band)", fontsize=9)
ax.axhline(10454.4, c="k", lw=1.2, ls="--")
w = (1300, 13060, 6200, 13240)
ax = axs.flat[3]; parts(ax, dplan, *w, cores=False); vss(ax, w[1], w[3])
for c in dplan["die"]["channels"]:
    if "rect_um" in c and "R16 centre" in c.get("reason", ""):
        x0, y0, x1, y1 = c["rect_um"]; ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fc="#bfe3ff", ec="#1f77b4", alpha=0.5))
ax.set_xlim(w[0], w[2]); ax.set_ylim(w[1], w[3])
nx = sum(1 for c in dplan["die"]["channels"] if "_cc_" in c.get("name", ""))
ax.set_title(f"plan delta: 43.2-um centre channel [1563.84, 13132.8 .. 13176.0] (blue, 5 VSS lanes); {nx} declared crossings M4-M7", fontsize=9)
fig.suptitle("INFRA-FIRST-QC-R16 (UNCHECKED): red = M8 VSS 8.64k; green M8 / blue M9 legs; magenta = dry plan error; tan = hard cores", fontsize=10)
fig.savefig(out, bbox_inches="tight")
print(out)
