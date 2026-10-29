import sys, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
dump, out = sys.argv[1], sys.argv[2]
hl = sys.argv[3:]  # substrings to highlight
xs = {"S": ([], []), "B": ([], []), "L": ([], []), "K": ([], [])}
mac = []; die = None; pins = []; hx = []
for line in open(dump):
    a = line.rstrip("\n").split("\t")
    if a[0] == "D": die = list(map(float, a[1:5]))
    elif a[0] == "C":
        k = a[2]; x0, y0, x1, y1 = map(float, a[4:8]); n = a[8] if len(a) > 8 else ""
        if k == "M": mac.append((x0, y0, x1, y1, a[3]))
        elif k in xs: xs[k][0].append((x0 + x1) / 2); xs[k][1].append((y0 + y1) / 2)
        if any(h in n for h in hl): hx.append(((x0 + x1) / 2, (y0 + y1) / 2))
    elif a[0] == "P": pins.append((float(a[6]), float(a[7])))
W, H = die[2] - die[0], die[3] - die[1]
fig, ax = plt.subplots(figsize=(6, 6 * H / W))
ax.add_patch(Rectangle((die[0], die[1]), W, H, fill=False, ec="k"))
for x0, y0, x1, y1, m in mac:
    ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fc="#ccd", ec="#447", lw=0.5))
col = {"S": "#d33", "B": "#3a3", "L": "#888", "K": "#00f"}
for k in ("L", "B", "S", "K"):
    ax.scatter(*xs[k], s=0.3, c=col[k], lw=0, label=f"{k} {len(xs[k][0])}")
if pins: ax.scatter(*zip(*pins), s=0.5, c="orange", lw=0, label=f"pins {len(pins)}")
if hx: ax.scatter(*zip(*hx), s=30, marker="x", c="m", label="highlight")
ax.set_xlim(die[0], die[2]); ax.set_ylim(die[1], die[3]); ax.set_aspect("equal")
ax.legend(loc="upper right", fontsize=6, markerscale=10); ax.set_title(out.split("/")[-1], fontsize=8)
fig.savefig(out, dpi=150, bbox_inches="tight")
