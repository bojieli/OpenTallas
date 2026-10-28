import json, re, sys
from pathlib import Path
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
out = sys.argv[1]; pairs = sys.argv[2:]
fig, axs = plt.subplots(1, len(pairs) // 2, figsize=(7 * len(pairs) // 2, 9))
for ax, (mpf, kd) in zip(axs, zip(pairs[::2], pairs[1::2])):
    kd = Path(kd)
    cfg = {m.group(1): m.group(2).strip() for m in re.finditer(r"^export\s+(\w+)\s*=\s*(.*)$", (kd / "config.mk").read_text(), re.M)}
    dx0, dy0, dx1, dy1 = map(float, cfg["DIE_AREA"].split())
    cx0, cy0, cx1, cy1 = map(float, cfg["CORE_AREA"].split())
    ax.add_patch(Rectangle((dx0, dy0), dx1 - dx0, dy1 - dy0, fill=False, ec="k"))
    ax.add_patch(Rectangle((cx0, cy0), cx1 - cx0, cy1 - cy0, fill=False, ec="gray", ls="--"))
    d = json.load(open(mpf))
    src = json.load(open(mpf.replace("mp3_", "mp_")))["macro_placement"]
    W, H = 94.824, 41.064
    for m, s in zip(d["macro_placement"], sorted(src, key=lambda q: q["k"])):
        pass
    so = {q["k"]: q["origin_um"] for q in src}
    for m in d["macro_placement"]:
        x, y = m["origin_um"]; ax.add_patch(Rectangle((x, y), W, H, fc="#7fb3ff", ec="b", alpha=.8))
        x0, y0 = so[m["k"]]; ax.add_patch(Rectangle((x0, y0), W, H, fill=False, ec="orange", lw=.6, ls=":"))
        if m["moved_um"] > 1: ax.annotate("", (x, y), (x0, y0), arrowprops=dict(arrowstyle="->", color="orange", lw=.6))
    for c in json.load(open(kd / "core_infra_plan.json"))["cells"]:
        r = c["rect_um"]; ax.add_patch(Rectangle((r[0], r[1]), r[2] - r[0], r[3] - r[1], fc="red", ec="red"))
    rp = d["report"]
    ax.set_title(f"{kd.name[:40]}\nmacros {rp['macros']} cols {rp['columns']} max move {rp['max_move_um']} mean {rp['mean_move_um']}\n"
                 f"blue=fixed  dotted orange=RTLMP src  red=islands", fontsize=8)
    ax.set_xlim(dx0 - 5, dx1 + 5); ax.set_ylim(dy0 - 5, dy1 + 5); ax.set_aspect("equal")
plt.tight_layout(); plt.savefig(out, dpi=110)
print(out)
