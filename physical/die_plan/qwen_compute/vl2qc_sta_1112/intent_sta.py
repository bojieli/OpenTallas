"""VL2QC-STA intent figure: base vs form for one st_a type (outline, landing/collector bands, ft face windows, hard
cores; moved cores red, old sites dashed). usage: intent_sta.py BASE.json FORM.json TYPE OUT_PREFIX  -> .svg + .png"""
import json, sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
b, f, tn, out = sys.argv[1:5]
B = json.load(open(b))["partition_types"][tn]; F = json.load(open(f))["partition_types"][tn]
fig, axs = plt.subplots(1, 2, figsize=(11, 12), sharey=True)
for ax, T, title in ((axs[0], B, "s25 (before)"), (axs[1], F, "VL2QC-STA form (after)")):
    W, H = T["outline_um"]
    ax.add_patch(Rectangle((0, 0), W, H, fill=False, lw=1.5))
    lc = T["clock"]["landing_contract"]
    for n, bd in lc["bands"].items():
        x0, y0, x1, y1 = bd["rect_um"]
        ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, color="tab:green", alpha=0.35))
        ax.text(x0, y1 + 3, n, fontsize=6, color="darkgreen")
    bo = {h["inst"]: h for h in B["hard_cores"]}
    for h in T["hard_cores"]:
        x, y = h["origin_um"]; w, hh = h["outline_um"]
        moved = bo[h["inst"]]["origin_um"] != F_h if False else None
        fo = {g["inst"]: g for g in F["hard_cores"]}[h["inst"]]
        mv = bo[h["inst"]]["origin_um"] != fo["origin_um"]
        ax.add_patch(Rectangle((x, y), w, hh, color=("tab:red" if mv else "0.6"), alpha=0.8))
        ax.plot([x + 0.5, x + 0.5], [y, y + hh], color="k", lw=1.2)  # W-edge pins (R0)
        if mv and T is F:
            ox, oy = bo[h["inst"]]["origin_um"]
            ax.add_patch(Rectangle((ox, oy), w, hh, fill=False, ls="--", ec="tab:red"))
            ax.annotate("", (x + w / 2, y + hh / 2), (ox + w / 2, oy + hh / 2), arrowprops=dict(arrowstyle="->", color="tab:red", lw=0.8))
    for s in T.get("ft_slots") or []:
        for side in ("in", "out"):
            pass
    ax.set_xlim(-10, W + 10); ax.set_ylim(-10, 700); ax.set_aspect("equal"); ax.set_title(f"{tn}\n{title}", fontsize=9)
    ax.set_xlabel("x um (type-local)")
fig.text(0.5, 0.02, "red = moved hard cores (r0 SRAM group + btab[0]); dashed = old site; green = landing/collector bands; black edge line = SRAM pin edge (W, R0)",
         ha="center", fontsize=8)
fig.savefig(out + ".svg"); fig.savefig(out + ".png", dpi=90)
print("wrote", out)
