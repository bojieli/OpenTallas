import json, sys, collections, numpy as np, matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
fig, axs = plt.subplots(1, 2, figsize=(16, 8))
for ax, (f, name) in zip(axs, [(sys.argv[1], "qkd_kvs_pc"), (sys.argv[2], "qkd_kvs_pc_h_head_p")]):
    P = json.load(open(f)); W, H = 397.44, 362.88
    buses = sorted({p["bus"] for p in P}); cm = plt.get_cmap("tab20")
    for i, b in enumerate(buses):
        q = [p for p in P if p["bus"] == b]
        ax.scatter([p["x"] for p in q], [p["y"] for p in q], s=4, color=cm(i % 20), label=f"{b} {len(q)}" if len(q) > 40 or 'ck' in b else None)
    for p in P:
        if p["bus"] in ("ck", "hck", "rst_n", "hrst_n"): ax.scatter(p["x"], p["y"], s=150, marker="*", c="red"); ax.text(p["x"]+3, p["y"]-10, p["bus"], color="red")
    ax.add_patch(plt.Rectangle((0, 0), W, H, fill=False)); ax.set_xlim(-10, W+10); ax.set_ylim(-10, H+10); ax.set_aspect("equal")
    st = collections.Counter(p["face"] for p in P)
    dens = {fc: round(st[fc] / ((W if fc in "NS" else H)), 2) for fc in st}
    ax.set_title(f"{name}: {len(P)} pins, per face {dict(st)}, pins/um {dens}", fontsize=8); ax.legend(fontsize=5, loc="center", markerscale=3)
    print(name, dict(st), dens)
plt.savefig(sys.argv[3], dpi=80, bbox_inches="tight")
