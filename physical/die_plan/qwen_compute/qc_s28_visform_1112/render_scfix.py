import json, sys
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
X = json.load(open(sys.argv[1])); out = sys.argv[2]
types = list(X["before"])
fig, axs = plt.subplots(len(types), 2, figsize=(11, 9 * len(types)))
cols = {}
pal = ["#d62728", "#1f77b4", "#2ca02c", "#9467bd", "#ff7f0e", "#8c564b", "#e377c2", "#17becf", "#7f7f7f", "#bcbd22"]
for r, tn in enumerate(types):
    for c, side in enumerate(("before", "after")):
        ax = axs[r][c] if len(types) > 1 else axs[c]; t = X[side][tn]; W, H = t["outline_um"]
        ax.add_patch(Rectangle((0, 0), W, H, fc="none", ec="k"))
        for h in t["cores"]:
            ax.add_patch(Rectangle((h[0], h[1]), h[2] - h[0], h[3] - h[1], fc="#dddddd", ec="#555"))
        for s in t["slots"]:
            col = cols.setdefault(s["name"], pal[len(cols) % len(pal)])
            hi = s["name"] in X["moved"].get(tn, [])
            for b in s["blocks"]:
                ax.add_patch(Rectangle((b[0], b[1]), b[2] - b[0], b[3] - b[1], fc=col, ec="k" if hi else "none", alpha=0.85 if hi else 0.35, lw=1.2))
            pts = [(0.0, (s["in_window_um"][0] + s["in_window_um"][1]) / 2)] if s["in_face"] == "W" else []
            pts += [tuple(p) for p in s["regs"]]
            if s["out_face"] == "E":
                pts.append((W, (s["out_window_um"][0] + s["out_window_um"][1]) / 2))
            if hi:
                ax.plot([p[0] for p in pts], [p[1] for p in pts], "-o", color=col, lw=1.6, ms=3, label=s["name"])
        ax.set_xlim(-10, W + 10); ax.set_ylim(500, 1600); ax.set_aspect("equal")
        ax.set_title(f"{tn} {side}\ngrey = u_core; outlined blocks = re-sited stations; line = reg chain to E window centre", fontsize=8)
        ax.legend(fontsize=7, loc="lower left")
fig.tight_layout(); fig.savefig(out, dpi=100); print("ok")
