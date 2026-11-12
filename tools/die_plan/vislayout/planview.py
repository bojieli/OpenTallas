"""planview.py OUT.png TYPE LABEL1=PLAN1 [LABEL2=PLAN2 ...] : side-by-side plan view of a type (hard cores, die islands,
ft station bit sites + station-centroid legs coloured by width)."""
import json, sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

out, typ = sys.argv[1], sys.argv[2]
pairs = [a.split("=", 1) for a in sys.argv[3:]]
fig, axes = plt.subplots(1, len(pairs), figsize=(7 * len(pairs), 8.5))
if len(pairs) == 1:
    axes = [axes]
for ax, (lab, pf) in zip(axes, pairs):
    t = json.load(open(pf))["partition_types"][typ]
    W, H = t["outline_um"]
    ax.add_patch(Rectangle((0, 0), W, H, fill=False, ec="k"))
    for c in t.get("hard_cores", []):
        x, y = c["origin_um"]; w, h = c.get("size_um") or c.get("outline_um")
        ax.add_patch(Rectangle((x, y), w, h, fc="#ccc", ec="#555", hatch="//", lw=0.6))
        ax.text(x + w / 2, y + h / 2, c["inst"], ha="center", va="center", fontsize=6)
    for r in (t.get("clock", {}).get("die_islands_um") or []):
        ax.add_patch(Rectangle((r[0], r[1]), r[2] - r[0], max(r[3] - r[1], 3), fc="m", ec="m"))
    for f in t.get("ft_slots", []):
        w = f.get("width", 1)
        col = "red" if w >= 500 else ("orange" if w >= 40 else "blue")
        cents = []
        for st in f.get("bit_sites_um") or []:
            pts = [p for p in st if isinstance(p, list) and len(p) == 2]
            if not pts:
                continue
            xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
            ax.scatter(xs, ys, s=0.2, c=col)
            cents.append((sum(xs) / len(xs), sum(ys) / len(ys)))
        for (a, b), (c2, d) in zip(cents, cents[1:]):
            ax.plot([a, c2, c2], [b, b, d], c=col, lw=1.2 if w >= 40 else 0.5)
        if cents and w >= 40:
            ax.text(cents[0][0], cents[0][1], "%s(%d)" % (f["name"], w), fontsize=7, color=col)
    ax.set_xlim(-20, W + 20); ax.set_ylim(-20, H + 20); ax.set_aspect("equal"); ax.set_title("%s %s" % (typ, lab), fontsize=9)
plt.tight_layout(); plt.savefig(out, dpi=110)
print("wrote", out)
