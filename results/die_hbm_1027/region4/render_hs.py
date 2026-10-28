import json, sys, matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt, colorsys
P = json.load(open(sys.argv[1])); M = json.load(open(sys.argv[2]))["part_region"]; R = json.load(open(sys.argv[3]))
T = P["partition_types"]; regs = sorted(set(M.values())); col = {g: colorsys.hsv_to_rgb((i * 0.618) % 1, .45, .95) for i, g in enumerate(regs)}
f, ax = plt.subplots(figsize=(16, 8))
for p in P["partitions"]:
    w, h = T[p["type"]]["outline_um"]; x, y = p["origin_um"]; g = M[p["name"]]
    ax.add_patch(plt.Rectangle((x, y), w, h, fc=col[g], ec="k", lw=1.2 if T[p["type"]]["hard"] else .4, hatch="//" if T[p["type"]]["hard"] else None))
    ax.text(x + w / 2, y + h / 2, f"{g}\n{p['name']}", ha="center", va="center", fontsize=5)
for n, r in R.items():
    ax.axvline(r["cut_abs_x"], color="r", lw=2, ymin=0, ymax=1, ls="--")
o = P["die"]["outline_um"]; ax.set_xlim(0, o[0] if len(o) == 2 else o[2]); ax.set_ylim(0, o[1] if len(o) == 2 else o[3]); ax.set_aspect("equal")
ax.set_title("HBM C20f region map tok_l10_v1_c5 + hub W/E split (red dashed = hub cuts; hatched = hard partitions)")
plt.savefig(sys.argv[4], dpi=110, bbox_inches="tight")
