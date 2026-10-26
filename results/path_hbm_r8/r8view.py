#!/usr/bin/env python3
"""PATH-HBM-R8 renders: hub layouts (old vs distributed) + cut-use profiles before/after."""
import json
import sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402
sys.path.insert(0, sys.argv[1])
import plan_cut as PC  # noqa: E402
import numpy as np  # noqa: E402

old = json.load(open(sys.argv[2]))["partition_types"]
new = json.load(open(sys.argv[3]))["partition_types"]
out = sys.argv[4]
hubs, banks = ["q_hub_nw", "q_hub_ne"], ["q_b100", "q_b101", "q_b102", "q_b103"]


def layout(ax, t, title, S=None):
    W, H = t["outline_um"]
    ax.add_patch(Rectangle((0, 0), W, H, fill=False, lw=1))
    for h in t["hard_cores"]:
        x, y = h["origin_um"]
        w, hh = h["outline_um"]
        c = "#c44" if "__s" in h["inst"] else "#48a"
        ax.add_patch(Rectangle((x, y), w, hh, fc=c, ec="k", lw=0.3, alpha=0.6))
    for s in t["internal_stations"][::7]:
        p = [s["from_um"]] + s.get("regs_um", []) + [s["to_um"]]
        ax.plot([q[0] for q in p], [q[1] for q in p], lw=0.15, c="#2a2", alpha=0.4)
    if S:
        for k in range(1, S):
            ax.axvline(W * k / S, c="m", ls="--", lw=0.8)
    ax.set_xlim(-50, W + 50)
    ax.set_ylim(-50, H + 50)
    ax.set_aspect("equal")
    ax.set_title(title, fontsize=8)


def prof(t, ax_):
    W, H = t["outline_um"]
    nets = PC._nets(t)
    cores = PC._cores(t)
    X = np.arange(PC.STEP, W - 1e-6, PC.STEP) if ax_ == "x" else np.arange(PC.STEP, H - 1e-6, PC.STEP)
    r = PC._cut_profile(W, H, nets, cores)
    # recompute the full profile (plan_cut returns max only)
    d = np.zeros(len(X))
    for n in nets:
        vs = [p[0 if ax_ == "x" else 1] for p in n["pts"]]
        d[(X > min(vs)) & (X < max(vs))] += n["bits"]
    f = 0.75
    b = np.zeros(len(X))
    for (x0, y0, x1, y1) in cores.values():
        if ax_ == "x":
            b[(X > x0) & (X < x1)] += min(y1, H) - max(y0, 0)
        else:
            b[(X > y0) & (X < y1)] += min(x1, W) - max(x0, 0)
    L = H if ax_ == "x" else W
    b = np.minimum(b, L)
    c = (L - b) * f / 0.048 + L * f / 0.064
    return X, d / c, r[ax_]["max_use"]


fig = plt.figure(figsize=(16, 13))
gs = fig.add_gridspec(4, 2)
S = int(sys.argv[5]) if len(sys.argv) > 5 else None
for i, h in enumerate(hubs):
    layout(fig.add_subplot(gs[i, 0]), old[h], f"{h} plan_b1e2 (star hub)")
    layout(fig.add_subplot(gs[i, 1]), new[h], f"{h} R8 distributed S={S} (red = per-segment copies)", S)
ax = fig.add_subplot(gs[2, :])
for h in hubs:
    for src, ls in ((old, "-"), (new, "--")):
        X, u, m = prof(src[h], "x")
        ax.plot(X, u, ls, lw=0.8, label=f"{h} {'b1e2' if src is old else 'R8'} x-cut max {m}")
ax.axhline(0.6, c="r")
ax.set_ylabel("x-cut use (lower bound)")
ax.set_yscale("log")
ax.legend(fontsize=7)
ax = fig.add_subplot(gs[3, :])
for h in banks:
    for src, ls in ((old, "-"), (new, "--")):
        X, u, m = prof(src[h], "y")
        ax.plot(X, u, ls, lw=0.8, label=f"{h} {'b1e2' if src is old else 'R8 k=4'} y-cut max {m}")
ax.axhline(0.6, c="r")
ax.set_ylabel("bank y-cut use")
ax.set_xlabel("cut position um")
ax.legend(fontsize=7, ncol=2)
fig.tight_layout()
fig.savefig(out, dpi=110)
print(out)
