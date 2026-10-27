import json, sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
d, out = sys.argv[1], sys.argv[2]
M = json.load(open(d + "/mesh.json")); P = json.load(open(d + "/place.json")); N = json.load(open(d + "/nets.json"))["nets"]
fig, axs = plt.subplots(1, 3, figsize=(18, 6))
wins = [(10200, 11900), (20200, 21900), (29900, 31700)]
br = {r["root"]: r for r in M["band_roots"]}
nodes = {n["drv"] for n in N if n["drv"] in P and any(l in br for l in n["loads"])}
for ax, (x0, x1) in zip(axs, wins):
    for y in M["ys"]:
        ax.axhline(y, color="#9ab", lw=0.5)
    for x in M["xs"]:
        if x0 <= x <= x1:
            ax.axvline(x, color="#9ab", lw=0.5, ls=":")
    for n in N:
        if n["drv"] in br or n["drv"] in nodes:
            a = P[n["drv"]]
            for l in n["loads"]:
                if l in P:
                    b = P[l]
                    ax.plot([a["x"], a["x"], b["x"]], [a["y"], b["y"], b["y"]], color="m" if n["drv"] in br else "r", lw=1)
    for t in M["taps"]:
        if t.get("band_tree") and x0 <= t["xy"][0] <= x1:
            ax.plot(*t["xy"], "go", ms=4); ax.plot([t["foot"][0], t["xy"][0]], [t["foot"][1], t["xy"][1]], "g-", lw=0.8)
    for r in M["band_roots"]:
        if x0 <= r["foot"][0] <= x1:
            ax.plot(*r["foot"], "ms", ms=7)
            ax.annotate(f"in {r['input_um']:.0f}/comb {r['comb_max_um']:.0f}", r["foot"], fontsize=7, xytext=(4, 4), textcoords="offset points")
    for nn in nodes:
        q = P[nn]
        if x0 <= q["x"] <= x1:
            ax.plot(q["x"], q["y"], "r^", ms=7)
    ax.axhline(1331, color="k", lw=1, ls="--")
    ax.set_xlim(x0, x1); ax.set_ylim(0, 2000); ax.set_title(f"x {x0}-{x1}: band roots (magenta sq), leaf nodes (red tri), taps (green)", fontsize=8)
fig.suptitle("PATH-S81-PD8 md3 bottom band: leaf-fed band roots at plan-computed depth (all nets <= 600 um); dashed = core-field edge y 1331")
fig.tight_layout(); fig.savefig(out, dpi=100)
print(out)
