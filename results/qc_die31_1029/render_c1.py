# DIE-QC-31: render c1 M8/M9 near the column-1 strap: base vs vK vs vT (from dump_c1.py JSON)
import json, sys
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib.lines import Line2D
D = json.load(open(sys.argv[1])); out = sys.argv[2]
col = {"ck_mesh": "#888888", "n_P1u": "#d62728", "n_B1": "#1f77b4", "n_P1d": "#2ca02c", "n_C1u": "#9467bd", "n_D1ud": "#ff7f0e"}
fig, axs = plt.subplots(1, len(D), figsize=(5 * len(D), 9), sharey=True)
for ax, (f, shapes) in zip(axs, D.items()):
    for nn, L, x0, y0, x1, y1 in shapes:
        x0, x1 = max(x0, 542), min(x1, 549)
        if x1 <= x0: continue
        ax.add_patch(Rectangle((x0, y0), x1 - x0, max(y1 - y0, 1.5), color=col[nn], alpha=0.85 if L == "M9" else 0.4, lw=0))
    ax.set_xlim(542, 549); ax.set_ylim(900, 2100); ax.set_title(f.split("/")[-4] + ": c1 M9 solid / M8 light", fontsize=10)
    ax.set_xlabel("x um (mesh strap 546.40-546.56)")
axs[0].set_ylabel("y um")
fig.legend([Line2D([0], [0], color=c, lw=6) for c in col.values()], list(col), loc="lower center", ncol=6)
plt.tight_layout(rect=(0, 0.04, 1, 1)); plt.savefig(out, dpi=80); print("wrote", out)
