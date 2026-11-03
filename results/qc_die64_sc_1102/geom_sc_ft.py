"""DIE-QC-64/SC GEOM render: SC type outline, hard core + pins, clock taps, ft station bit sites (exact) per slot."""
import json, sys
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
plan, pdir, out = sys.argv[1:4]
types = sys.argv[4].split(",")
P = json.load(open(plan))
fig, axs = plt.subplots(1, len(types), figsize=(7 * len(types), 15))
axs = [axs] if len(types) == 1 else axs
stat = {}
for ax, t in zip(axs, types):
    T = P["partition_types"][t]; W, H = T["outline_um"]
    ax.add_patch(Rectangle((0, 0), W, H, fill=False, lw=2, ec="k"))
    boxes = []
    for hc in T["hard_cores"]:
        o = hc["origin_um"]; w, h = hc["outline_um"]
        boxes.append((o[0], o[1], o[0] + w, o[1] + h))
        ax.add_patch(Rectangle(o, w, h, fc="#fdb", ec="#c50", lw=1.5, alpha=.6))
        ax.text(o[0] + 5, o[1] + h - 25, f"{hc['inst']} {hc['module']}\n{hc.get('params', {})}", fontsize=7)
        pins = json.load(open(pdir + "/" + hc["pins_file"]))["pins"]
        ax.scatter([o[0] + p["x"] for p in pins], [o[1] + p["y"] for p in pins], s=1, c="b")
    cols = plt.cm.tab20.colors
    nin = 0; nsite = 0
    for k, s in enumerate(T.get("ft_slots", [])):
        c = cols[k % 20]
        for st in s.get("bit_sites_um") or []:
            xs = [p[0] for p in st]; ys = [p[1] for p in st]
            ax.scatter(xs, ys, s=.3, color=c)
            nsite += len(st)
            nin += sum(1 for x, y in zip(xs, ys) if any(a < x < cc and b < y < d for a, b, cc, d in boxes))
        for r in s.get("regs_um") or []:
            ax.plot(r[0], r[1], "s", color=c, ms=3)
    for tp in T["clock"].get("taps", []):
        ax.plot(*tp["xy"], "x", c="purple", ms=9, mew=2)
    stat[t] = dict(bit_sites=nsite, bit_sites_in_core=nin, slots=len(T.get("ft_slots", [])),
                   stations=sum(int(s.get("stations", 1)) for s in T.get("ft_slots", [])))
    ax.set_xlim(-10, W + 10); ax.set_ylim(-10, H + 10); ax.set_aspect("equal")
    ax.set_title(f"{t} {W}x{H}: SC core + ft station bit sites\n{stat[t]}", fontsize=8)
fig.tight_layout(); fig.savefig(out, dpi=100)
print(json.dumps(stat))
