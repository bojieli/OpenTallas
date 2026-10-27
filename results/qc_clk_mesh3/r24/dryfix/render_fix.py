import json, sys
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
OFF, HW = 1.14, 0.32
box = (2172.0, 13195.0, 2183.0, 13226.0)
fig, axs = plt.subplots(1, 2, figsize=(10, 7))
for ax, (title, path) in zip(axs, [("guard51 baseline", sys.argv[1]), ("R24b fixed", sys.argv[2])]):
    m = json.load(open(path))
    for w in m["fixed_wires"]:
        n = len(w["segs"])
        for (L, x0, y0, x1, y1), mo, e in zip(w["segs"], w.get("shield_modes") or ["drawn"]*n, w.get("shield_ext") or [1.46]*n):
            if L != "M9": continue
            e = 1.46 if e is None else e
            a0, a1 = min(y0, y1), max(y0, y1)
            if x0 < box[0]-3 or x0 > box[2]+3 or a1 < box[1] or a0 > box[3]: continue
            ax.add_patch(Rectangle((x0-HW, a0-HW), 2*HW, a1-a0+2*HW, fc="#d62728", alpha=0.7))
            ax.text(x0, min(max(a0, box[1]+1), box[3]-1), w["name"].replace("ckm_w_ckt_", ""), fontsize=7, rotation=90, ha="center")
            if mo == "drawn":
                for s in (-1, 1):
                    ax.add_patch(Rectangle((x0+s*OFF-0.32, a0-e), 0.64, a1-a0+2*e, fc="#1f77b4", alpha=0.45))
    ax.set_xlim(box[0], box[2]); ax.set_ylim(box[1], box[3]); ax.set_title(title + " (M9: red clock, blue VSS shield)")
    ax.set_aspect("auto"); ax.grid(alpha=0.3)
plt.tight_layout(); plt.savefig(sys.argv[3], dpi=110)
