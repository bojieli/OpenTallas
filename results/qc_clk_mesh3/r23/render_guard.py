"""R22 render: centre clock channel near the root (x 14300-16500), M8/M9 segments of channel clock nets + cells + stacks."""
import json, sys
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
X0, X1, Y0, Y1 = 14300, 16500, 13125, 13190
fig, axs = plt.subplots(len(sys.argv) - 2, 1, figsize=(16, 4.2 * (len(sys.argv) - 2)))
for ax, d in zip([axs] if len(sys.argv)==3 else axs, sys.argv[2:]):
    M = json.load(open(f"{d}/mesh.json")); P = json.load(open(f"{d}/place.json"))
    ax.add_patch(Rectangle((X0, 13132.8), X1 - X0, 51.84, fc="#eef6ff", ec="b", lw=1))
    for k in range(6):
        ax.axhline(13132.8 + 8.64 * k, color="0.8", lw=0.5, ls=":")
    for w in M["fixed_wires"]:
        for s in w["segs"]:
            L, x0, y0, x1, y1 = s[:5]
            if max(x0, x1) < X0 or min(x0, x1) > X1 or max(y0, y1) < Y0 or min(y0, y1) > Y1:
                continue
            ax.plot([x0, x1], [y0, y1], color="r" if L == "M8" else "g", lw=1.5)
        for st in w.get("stacks", []):
            x, y = st["xy"]; ry = st["riser_from"][1]
            if X0 <= x <= X1 and Y0 <= y <= Y1:
                bad = not (13132.8 <= ry <= 13184.64)
                ax.plot([x, x], [y, ry], color="m" if bad else "k", lw=2.5 if bad else 0.8)
                if bad:
                    ax.plot(x, y, "mx", ms=10)
    for c, v in P.items():
        if X0 <= v["x"] <= X1 and Y0 <= v["y"] <= Y1:
            ax.add_patch(Rectangle((v["x"], v["y"]), 1.6, 0.27, fc="orange", ec="k", lw=0.3))
    ax.set_xlim(X0, X1); ax.set_ylim(Y0, Y1); ax.set_title(f"{d}: channel (blue), M8 red, M9 green, risers black / OUTSIDE magenta x")
plt.tight_layout(); plt.savefig(sys.argv[1], dpi=90)
