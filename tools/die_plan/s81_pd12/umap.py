"""PD12 render: per-load worst neighbour-pair U (<=1 mm) maps for mesh what-ifs (model, UNCHECKED)."""
import json, math, sys
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
place, recp, out = sys.argv[1:4]; runs = sys.argv[4:]
P = json.load(open(place)); rec = json.load(open(recp)); rx, ry = rec["root_xy"]
fig, axs = plt.subplots(1, len(runs), figsize=(6 * len(runs), 4.8))
for ax, r in zip(axs, runs):
    lab, f = r.split("=")
    S = json.load(open(f)); L = S["loads"]; arr = S["arr"]; gv = S["grad_vec_ps"]; ns = len(arr)
    idx = [i for i, k in enumerate(L) if k in P and not k.startswith("ckm_br_")]
    xy = {i: (P[L[i]]["x"], P[L[i]]["y"]) for i in idx}
    cell = {}
    for i in idx: cell.setdefault((int(xy[i][0] // 1000), int(xy[i][1] // 1000)), []).append(i)
    worst = {i: 0.0 for i in idx}
    for i in idx:
        x, y = xy[i]
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for j in cell.get((int(x // 1000) + dx, int(y // 1000) + dy), []):
                    if j <= i or abs(x - xy[j][0]) + abs(y - xy[j][1]) > 1000: continue
                    ds = [arr[s][i] - arr[s][j] for s in range(ns)]; m = ds[1:]; mu = sum(m) / len(m)
                    sd = (sum((v - mu) ** 2 for v in m) / max(1, len(m) - 1)) ** .5
                    u = max(max(abs(v) for v in ds), abs(mu) + 3 * sd) + math.hypot(gv[i][0] - gv[j][0], gv[i][1] - gv[j][1])
                    worst[i] = max(worst[i], u); worst[j] = max(worst[j], u)
    sc = ax.scatter([xy[i][0] / 1e3 for i in idx], [xy[i][1] / 1e3 for i in idx], c=[worst[i] for i in idx], s=3,
                    cmap="inferno", vmin=0, vmax=250)
    ax.axvline(rx / 1e3, color="c", lw=0.5); ax.axhline(ry / 1e3, color="c", lw=0.5)
    ax.set_title(f"{lab}: max U {max(worst.values()):.0f} ps, >80: {sum(v > 80 for v in worst.values())} loads", fontsize=9)
    ax.set_xlabel("x mm"); ax.set_ylabel("y mm"); ax.set_aspect("equal")
fig.colorbar(sc, ax=axs, label="worst neighbour-pair U (ps, TT, gap term excluded)")
fig.savefig(out, dpi=110)
