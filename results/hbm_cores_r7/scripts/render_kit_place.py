"""HBM-CORES-R6 generic placed-core render: kit placed.csv (dump_placed.py) + outline/core from config.mk + master-slice
clock island + pin faces.  usage: render_kit_place.py KIT out.png [--title T]"""
import argparse, csv, json, re
from pathlib import Path
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
ap = argparse.ArgumentParser(); ap.add_argument("kit"); ap.add_argument("png"); ap.add_argument("--title", default="")
a = ap.parse_args(); K = Path(a.kit)
cfg = (K / "config.mk").read_text()
die = [float(v) for v in re.search(r"DIE_AREA = (.+)", cfg).group(1).split()]
core = [float(v) for v in re.search(r"CORE_AREA = (.+)", cfg).group(1).split()]
W, H = die[2], die[3]
fig, ax = plt.subplots(figsize=(min(16, 4 + W / 25), min(16, 2 + H / 25)))
ax.add_patch(Rectangle((0, 0), W, H, fill=False, lw=1)); ax.add_patch(Rectangle(core[:2], core[2] - core[0], core[3] - core[1], fill=False, lw=0.5, ls="--"))
pts = {k: ([], []) for k in ("std", "ff", "buf", "tap")}; pins = ([], [], []); area = 0.0; nm = 0
for r in csv.DictReader(open(K / "placed.csv")):
    k = r["kind"]; x, y = float(r["x"]), float(r["y"])
    if k == "macro":
        nm += 1; ax.add_patch(Rectangle((x, y), float(r["w"]), float(r["h"]), fc="#c8c8e8", ec="k", lw=0.8))
        ax.text(x + 2, y + 2, r["name"][-40:].replace("\\", ""), fontsize=5)
    elif k in pts:
        pts[k][0].append(x); pts[k][1].append(y)
        if k != "tap": area += float(r["w"]) * float(r["h"])
    elif k == "pin":
        pins[0].append(x); pins[1].append(y); pins[2].append("red" if re.match(r"clk", r["name"]) else "green")
for k, c in (("tap", "#dddddd"), ("std", "#888888"), ("buf", "#2a8"), ("ff", "#36c")):
    ax.scatter(*pts[k], s=0.4, c=c, label=f"{k} {len(pts[k][0])}", lw=0)
ax.scatter(pins[0], pins[1], s=3, c=pins[2], marker="s", lw=0, label=f"pins {len(pins[0])}")
ms = json.loads((K / "master_slice.json").read_text()) if (K / "master_slice.json").is_file() else {}
for i in ms.get("islands", []):
    x0, y0, x1, y1 = i["rect_um"]; ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fill=False, ec="r", lw=1))
    if i.get("clock_pin"): ax.plot(*i["clock_pin"]["xy_um"], "r*", ms=10)
ca = (core[2] - core[0]) * (core[3] - core[1])
ax.set_xlim(-3, W + 3); ax.set_ylim(-3, H + 3); ax.set_aspect("equal"); ax.legend(loc="upper right", fontsize=6, markerscale=6)
ax.set_title(f"{a.title}  {W:g}x{H:g} um, {nm} macros, std-cell area {area:.0f} um2 = {area / ca:.2f} of core (excl. macros)", fontsize=8)
fig.savefig(a.png, dpi=150, bbox_inches="tight"); print("wrote", a.png, "stdcell_area", round(area, 1), "core", round(ca, 1))
