import json, sys
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
pd, out = sys.argv[1], sys.argv[2]
cm = json.load(open(pd + "/core_macros.json"))["cores"]; ce = json.load(open(pd + "/clock_entries.json"))
mods = ["ot_hgi_sfu_core_split3__opstore_a", "ot_hgi_sfu_core_split3__opstore_b"]
fig, axs = plt.subplots(1, 2, figsize=(16, 7))
for ax, m in zip(axs, mods):
    W, H = cm[m]["outline_um"]
    ax.add_patch(Rectangle((0, 0), W, H, fill=False, lw=2))
    for r in cm[m]["macros"]:
        x0, y0, x1, y1 = r["rect_um"]; ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fc="#7fa7d9", ec="k", lw=.5))
    for blk in ce.values():
        for e in (blk.values() if isinstance(blk, dict) else []):
            if isinstance(e, dict) and e.get("module") == m:
                i = e["island_um"]; ax.add_patch(Rectangle((i[0], i[1]), i[2] - i[0], i[3] - i[1], fc="r"))
    ax.set_xlim(-10, 990); ax.set_ylim(-10, 700); ax.set_aspect("equal"); ax.set_title(f"{m.split('__')[-1]} {W}x{H} {len(cm[m]['macros'])} macros")
fig.suptitle(sys.argv[3]); fig.savefig(out, dpi=70, bbox_inches="tight")
