"""render a head_tree_plan spec: sinks, macros, legs (L routes), leaves coloured by predicted TT rise."""
import sys, json
sys.path.insert(0, sys.argv[5]); import common
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
spec, geo, pred, out = sys.argv[1:5]
S = common.parse_spec(spec); sinks, macs, entry = common.parse_geo(geo); P = json.load(open(pred))
fig, ax = plt.subplots(figsize=(10, 10))
xs = [v[0] for v in sinks.values()]; ys = [v[1] for v in sinks.values()]
ax.scatter(xs[::3], ys[::3], s=0.3, c="0.75")
for m, v in macs.items():
    x0, y0, x1, y1 = v["rect"]; ax.add_patch(plt.Rectangle((x0, y0), x1 - x0, y1 - y0, color="0.85", ec="k")); ax.text(x0 + 2, y1 - 6, m, fontsize=8)
    ax.plot(*v["pin"], "ks", ms=4)
pos = {"root": S["root"]}; pos.update({n: v["xy"] for n, v in S["tree"].items()}); pos.update({n: v["xy"] for n, v in S["leaves"].items()})
par = {n: v["par"] for n, v in S["tree"].items()}; par.update({n: v["par"] for n, v in S["leaves"].items()})
def lvl(n):
    d = 0
    while n != "root": d += 1; n = par[n]
    return d
cols = ["r", "darkorange", "g", "b", "m", "c"]
for n, p in par.items():
    a, b = pos[p], pos[n]; c = cols[min(lvl(p), 5)]
    lw = 2.5 if lvl(p) == 0 else 1.2 if lvl(p) == 1 else 0.6
    ax.plot([a[0], b[0], b[0]], [a[1], a[1], b[1]], c, lw=lw, alpha=0.8)
lv = {n: (lambda q: q["rise"] if isinstance(q, dict) else q)(P["TT_leaf"][n]) for n in S["leaves"]}
sc = ax.scatter([pos[n][0] for n in lv], [pos[n][1] for n in lv], c=list(lv.values()), cmap="coolwarm", s=12, vmin=float(sys.argv[7]) if len(sys.argv) > 7 else 225, vmax=float(sys.argv[8]) if len(sys.argv) > 8 else 260, zorder=5)
plt.colorbar(sc, ax=ax, fraction=0.04, label="pred leaf TT rise ps (uf_phys3 v1 GRT, UNCHECKED)")
for n, v in S["tree"].items():
    if lvl(n) == 1: ax.plot(*v["xy"], "r^", ms=9, zorder=6)
ax.plot(*S["root"], "k*", ms=16, zorder=7)
D = max(max(v["rect"][2] for v in macs.values()), max(xs)) + 4; ax.set_xlim(0, 319.68 if D > 286 else 285.12); ax.set_ylim(0, 319.68 if D > 286 else 285.12); ax.set_aspect("equal")
ax.set_title(sys.argv[6] if len(sys.argv) > 6 else spec, fontsize=9)
fig.savefig(out, dpi=110, bbox_inches="tight")
