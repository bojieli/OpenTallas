"""Render per-type measured sinks (bins), hard macros and new density taps, small multiples (review image)."""
import json, sys, math
from pathlib import Path
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
ev, plan, out = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
tapsj = json.loads((ev / "new_taps.json").read_text()); P = json.load(open(plan))["partition_types"]
names = sorted(tapsj); n = len(names); cols = 10; rows = math.ceil(n / cols)
f, axs = plt.subplots(rows, cols, figsize=(cols * 2.4, rows * 4.2))
for ax, tn in zip(axs.flat, names):
    t = P[tn]; w, h = t["outline_um"]; ax.add_patch(Rectangle((0, 0), w, h, fill=False, lw=.6))
    for hc in t.get("hard_cores", []):
        if "origin_um" in hc and "outline_um" in hc:
            x, y = hc["origin_um"]; cw, ch = hc["outline_um"]
            if hc.get("orient", "R0") in ("R90", "R270", "MXR90", "MYR90"): cw, ch = ch, cw
            ax.add_patch(Rectangle((x, y), cw, ch, color="tab:blue", alpha=.3, lw=0))
    b = json.loads((ev / "bins" / f"{tn}.json").read_text())["bins"]
    ax.scatter([r[0] for r in b], [r[1] for r in b], s=[r[2] / 40 for r in b], c="gray", lw=0)
    tp = tapsj[tn]; ax.scatter([q[1] for q in tp], [q[2] for q in tp], s=6, c="red", marker="x", lw=.6)
    ax.set_xlim(-10, w + 10); ax.set_ylim(-10, h + 10); ax.set_aspect("equal"); ax.set_xticks([]); ax.set_yticks([])
    ax.set_title(f"{tn[:26]}\n{len(tp)} taps", fontsize=5)
for ax in list(axs.flat)[n:]: ax.axis("off")
f.savefig(out, dpi=90, bbox_inches="tight")
