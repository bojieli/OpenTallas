import json, sys, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
D = sys.argv[1]; R = "/srv/opentallas-scratch2/claude/codex-h2-window-1030"
old = {n[0]: n for n in json.load(open(R + "/tpqt_slew_geometry/plan_geometry.json"))[0]["nodes_xy"]}
new = {n[0]: n for n in json.load(open(D + "/model/plan_model.json"))[0]["nodes_xy"]}
fixed = []; pg = []
for l in open(R + "/baseline/sites.txt"):
    f = l.split()
    if f[0] == "FIXED" and len(f) >= 7 and "TAP" not in f[2]: fixed.append(tuple(map(float, f[3:7])))
    if f[0] == "PG" and f[2] == "M5": pg.append(tuple(map(float, f[3:7])))
def draw(ax, win=None):
    for a, b, c, d in fixed:
        if c - a > 3: ax.add_patch(Rectangle((a, b), c - a, d - b, fc="#ddd", ec="#888", lw=.3))
    for n, v in new.items():
        if v[1] is not None:
            p = new[v[1]][2]; ax.plot([p[0], v[2][0]], [p[1], v[2][1]], "-", c="#4a7", lw=.3)
    for n, v in new.items():
        o = old[n][2]; d = abs(o[0] - v[2][0]) + abs(o[1] - v[2][1])
        col = "r" if d > 5 else ("orange" if d > 2 else "b")
        ax.plot(*v[2], ".", c=col, ms=2 if win is None else 6)
        if d > 2: ax.annotate("", v[2], o, arrowprops=dict(arrowstyle="->", color=col, lw=.6))
    if win: ax.set_xlim(win[0], win[2]); ax.set_ylim(win[1], win[3])
    else: ax.set_xlim(0, 295.92); ax.set_ylim(0, 444.96)
    ax.set_aspect("equal")
worst = max(new, key=lambda n: abs(old[n][2][0] - new[n][2][0]) + abs(old[n][2][1] - new[n][2][1]))
wx, wy = new[worst][2]
fig, axs = plt.subplots(1, 2, figsize=(16, 11))
draw(axs[0]); axs[0].set_title("H2 tree on free native sites: blue<=2um, orange 2-5, red>5 um moved (arrow old->new)")
draw(axs[1], (wx - 25, wy - 25, wx + 25, wy + 25)); axs[1].set_title("zoom worst %s" % worst)
fig.tight_layout(); fig.savefig(D + "/conv/free_sites.png", dpi=110)
print("worst", worst, new[worst][2], old[worst][2])
