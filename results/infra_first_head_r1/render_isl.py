import json, sys
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
P = json.load(open(sys.argv[1])); I = json.load(open(sys.argv[2]))["detail"]; out = sys.argv[3]
zoom = len(sys.argv) > 4
fig, ax = plt.subplots(figsize=(14, 14))
T = P["partition_types"]
cols = {}
for q in P["partitions"]:
    w, h = T[q["type"]]["outline_um"]; x, y = q["origin_um"]
    ax.add_patch(Rectangle((x, y), w, h, fill=True, fc="#f3e6ee" if q["type"] == "hd_tile" else "#dde8f3", ec="#777", lw=0.3))
    if zoom:
        ax.text(x + 5, y + 5, f'{q["name"]} {q["orient"]}', fontsize=6)
    for c in T[q["type"]].get("hard_cores", []):
        s = 285.12 if "elemB" in c["module"] else 319.68
        cx, cy = c["origin_um"]
        if "elemB" in c["module"]: cx = 211.68
        o = q["orient"]
        X = x + cx if o in ("R0", "MX") else x + w - cx - s
        Y = y + cy if o in ("R0", "MY") else y + h - cy - s
        ax.add_patch(Rectangle((X, Y), s, s, fill=False, ec="#a33", lw=0.4))
for tn, v in I.items():
    for r in v["die_xy"]:
        for p in r[1:]:
            ax.plot(p[0], p[1], "s", ms=3 if not zoom else 6, color="#0a0" if tn == "hd_tile" else "#00c")
ax.set_xlim(0, P["die"]["outline_um"][0]); ax.set_ylim(0, P["die"]["outline_um"][1])
if zoom: ax.set_xlim(6500, 10200); ax.set_ylim(12500, 16300)
ax.set_aspect("equal"); ax.set_title("s81_head R1 in-core clock-entry islands (green: hd_tile core centres, blue: soft-type centre)")
fig.savefig(out, dpi=110, bbox_inches="tight")
