import json, sys, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
d = json.load(open(sys.argv[1])); out = sys.argv[2]
lanes = [(190.092, 34.572), (190.092, 354.252), (190.092, 725.772), (190.092, 1045.452)]
fig, axs = plt.subplots(1, 2, figsize=(12, 13), sharey=True)
for ax, key, title in ((axs[0], "before", "vA/vB reset relay hops (red = crosses a lane)"), (axs[1], "after", "vC re-site (no hop over a lane)")):
    ax.add_patch(Rectangle((0, 0), 622.08, 1339.2, fill=False, lw=1))
    for k, (x, y) in enumerate(lanes):
        ax.add_patch(Rectangle((x, y), 414.72, 267.84, color="#cfd8e3")); ax.text(x + 200, y + 130, f"lane{k}", ha="center")
    for r in d[key]:
        if r["q"].startswith("rn_"):
            continue
        (x0, y0), (x1, y1) = r["d_xy"], r["q_xy"]
        c = "red" if not r["lfree"] else "#2a7"
        # draw the free L if one exists, else x-then-y
        B = [(x - 4.32, y - 4.32, x + 419.04, y + 272.16) for x, y in lanes]
        def hit(p, q):
            lx, hx, ly, hy = min(p[0], q[0]), max(p[0], q[0]), min(p[1], q[1]), max(p[1], q[1])
            return any(lx < cc - 1e-6 and hx > a + 1e-6 and ly < dd - 1e-6 and hy > b + 1e-6 for a, b, cc, dd in B)
        m = (x1, y0)
        if hit((x0, y0), m) or hit(m, (x1, y1)):
            m = (x0, y1)
        ax.plot([x0, m[0], x1], [y0, m[1], y1], color=c, lw=1.6 if c == "red" else 0.9)
        ax.plot([x1], [y1], "o", ms=3, color=c)
    for k, (a, b) in d["moved"].items():
        if k.startswith("rn_"): continue
        if key == "after":
            ax.annotate("", xy=b, xytext=a, arrowprops=dict(arrowstyle="->", color="#a50", lw=0.8))
            ax.text(b[0] + 2, b[1] + 6, k.replace("rst_rl_", "u_rrl_"), fontsize=7, color="#a50")
    ax.set_title(title, fontsize=10); ax.set_aspect("equal"); ax.set_xlim(-10, 640); ax.set_ylim(-10, 1350)
fig.tight_layout(); fig.savefig(out, dpi=90)
