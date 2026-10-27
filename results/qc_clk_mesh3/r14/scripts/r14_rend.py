import json, sys
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
M = json.load(open(sys.argv[1] + "/mesh.json")); C = json.load(open(sys.argv[1] + "/place.json"))
r = [s["riser_um"] for w in M["fixed_wires"] for s in w.get("stacks", [])]
print("wires", len(M["fixed_wires"]), "stacks", len(r), "max riser", max(r), "meta tracks", M["meta"]["tree_tracks"]["modes"], "move_max", M["meta"]["tree_tracks"]["move_max_um"])
fig, ax = plt.subplots(figsize=(18, 5), dpi=120)
for y in [3913.92 + 4.32 * k for k in range(0, 10)]:
    ax.axhline(y, c="#f4a6a6" if round(y / 4.32) % 2 else "#9ecae1", lw=2.5, zorder=0)
cols = ["#1b9e77", "#d95f02", "#7570b3", "#e7298a", "#66a61e", "#e6ab02"]
for i, w in enumerate(M["fixed_wires"]):
    for s in w["segs"]:
        ax.plot([s[1], s[3]], [s[2], s[4]], lw=2.0 if s[0] == "M8" else 1.2, c=cols[i % 6] if s[0] == "M8" else "k", zorder=2)
    for st in w.get("stacks", []):
        ax.plot([st["riser_from"][0]] * 2, [st["riser_from"][1], st["xy"][1]], c="m", lw=1.0, zorder=3)
for n, c in C.items():
    ax.add_patch(Rectangle((c["x"], c["y"]), 1.62, 0.27, fc="#333", zorder=4))
ax.set_ylim(3912, 3954); ax.set_xlim(2150, 4060)
ax.set_title("R14 lane probe (UNCHECKED): period-0 local row x-tree, one 8.64-um lane per tree level, rows on VSS M8 phase; "
             "M8 trunks colour, M9 drops black, M7 risers magenta; PG M8 VSS blue / VDD red. dry build 0 errors", fontsize=9)
fig.savefig(sys.argv[2], bbox_inches="tight")
