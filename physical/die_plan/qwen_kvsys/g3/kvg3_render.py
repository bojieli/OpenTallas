"""KV-G3: render a kvg3_dump.py JSON (placed partition) for the geometry review + hop statistics.
usage: kvg3_render.py DUMP.json OUT.png [--title T] [--taps]   -> PNG + DUMP.stats.json"""
import argparse
import json
from collections import Counter

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402
from matplotlib.collections import LineCollection  # noqa: E402
import numpy as np  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("dump")
ap.add_argument("png")
ap.add_argument("--title", default="")
ap.add_argument("--taps", action="store_true", help="colour flops by their clock net (post-CTS)")
a = ap.parse_args()
d = json.load(open(a.dump))
x0, y0, x1, y1 = d["die"]
W, H = x1 - x0, y1 - y0
I = d["insts"]
cls = Counter(r[2] for r in I)
fig, axs = plt.subplots(1, 2, figsize=(22, 13), dpi=110, gridspec_kw=dict(width_ratios=[1.0, 1.0]))
ax = axs[0]
ax.add_patch(Rectangle((0, 0), W, H, fill=False, lw=1.2))
for r in I:
    if r[2] == "macro":
        ax.add_patch(Rectangle((r[3], r[4]), r[5] - r[3], r[6] - r[4], fc="khaki", ec="k", lw=0.5))
def pts(c):
    v = np.array([[(r[3] + r[5]) / 2, (r[4] + r[6]) / 2] for r in I if r[2] == c]) if cls.get(c) else np.zeros((0, 2))
    return v
b = pts("buf"); lg = pts("logic")
ax.scatter(b[:, 0], b[:, 1], s=0.15, c="0.65", lw=0, label=f"buf/inv {len(b)}")
ax.scatter(lg[:, 0], lg[:, 1], s=0.6, c="tab:orange", lw=0, label=f"logic {len(lg)}")
ffs = [r for r in I if r[2] == "ff"]
if a.taps and ffs:
    nets = sorted({r[7] for r in ffs})
    cm = plt.get_cmap("tab20")
    col = {n: cm(i % 20) for i, n in enumerate(nets)}
    ax.scatter([(r[3] + r[5]) / 2 for r in ffs], [(r[4] + r[6]) / 2 for r in ffs], s=0.5, lw=0,
               c=[col[r[7]] for r in ffs], label=f"FF {len(ffs)} (colour = clock net, {len(nets)} nets)")
else:
    f = pts("ff")
    ax.scatter(f[:, 0], f[:, 1], s=0.5, c="tab:blue", lw=0, label=f"FF {len(f)}")
P = d["pins"]
lay = Counter(p[1] for p in P)
ck = [p for p in P if p[0].startswith("clk")]
sig = [p for p in P if not p[0].startswith("clk")]
ax.scatter([p[2] for p in sig], [p[3] for p in sig], s=1.2, c="red", lw=0, label=f"signal pins {len(sig)}")
ax.scatter([p[2] for p in ck], [p[3] for p in ck], s=60, marker="*", c="magenta", label=f"clock taps {len(ck)}")
ax.set_xlim(-20, W + 20); ax.set_ylim(-20, H + 20); ax.set_aspect("equal")
ax.legend(loc="upper right", fontsize=8, markerscale=6)
ax.set_title(f"{a.title}  {W:.2f} x {H:.2f} um; cells {len(I)}: " + ", ".join(f"{k} {v}" for k, v in sorted(cls.items())), fontsize=9)
# right: reg-reg hop segments > 450 um + density heat map
ax2 = axs[1]
bins = 14.0
nx, ny = int(np.ceil(W / bins)), int(np.ceil(H / bins))
area = np.zeros((ny, nx))
for r in I:
    if r[2] in ("phys", "macro"):
        continue
    cx, cy = (r[3] + r[5]) / 2, (r[4] + r[6]) / 2
    ix, iy = min(nx - 1, max(0, int(cx / bins))), min(ny - 1, max(0, int(cy / bins)))
    area[iy, ix] += (r[5] - r[3]) * (r[6] - r[4])
dens = area / (bins * bins)
im = ax2.imshow(dens, origin="lower", extent=(0, nx * bins, 0, ny * bins), cmap="viridis", vmin=0, vmax=1.0)
fig.colorbar(im, ax=ax2, fraction=0.03, label="std-cell density per 14-um bin")
hops = d.get("hops", {})
st = {}
for k, L in hops.items():
    v = np.array([h[0] for h in L]) if L else np.zeros(0)
    st[k] = dict(n=int(len(v)), max=float(v.max()) if len(v) else 0.0, p90=float(np.percentile(v, 90)) if len(v) else 0.0,
                 p50=float(np.percentile(v, 50)) if len(v) else 0.0, over_675=int((v > 675).sum()), over_750=int((v > 750).sum()))
long = [h for L in hops.values() for h in L if h[0] > 450]
if long:
    ax2.add_collection(LineCollection([[h[3], h[4]] for h in long], colors="red", linewidths=0.3, alpha=0.6))
ax2.set_xlim(-20, W + 20); ax2.set_ylim(-20, H + 20); ax2.set_aspect("equal")
ax2.set_title("density (14-um bins) + hops > 450 um (red); " +
              "; ".join(f"{k}: n {v['n']} p90 {v['p90']:.0f} max {v['max']:.0f} >750 {v['over_750']}" for k, v in st.items()),
              fontsize=8)
st.update(cells=dict(cls), pins=dict(lay), max_bin_density=float(dens.max()), bins_over_0p8=int((dens > 0.8).sum()),
          worst_hops={k: sorted(L, reverse=True)[:5] for k, L in hops.items()})
fig.tight_layout()
fig.savefig(a.png)
json.dump(st, open(a.dump.replace(".json", "") + ".stats.json", "w"), indent=1, default=str)
print(json.dumps({k: v for k, v in st.items() if k != "worst_hops"}))
