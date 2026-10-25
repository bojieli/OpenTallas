#!/usr/bin/env python3
"""PATH-KV-ASTK2: 3_place zone render: placed.csv + astk_zone_delta.json -> PNG + JSON (per-zone flops in own box, wdec)."""
import csv, json, re, sys, statistics as st
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
d, kd, out = sys.argv[1:4]
W, H = 190.08, 181.44
boxes = json.load(open(f"{kd}/astk_zone_delta.json"))["regions"]
if len(sys.argv) > 4:   # the GPL boxes actually used (shrunk to group area) from the OT_ZONE_FENCE log lines
    for m in re.finditer(r"OT_ZONE_FENCE ot_zone_fence_(\w+) cells \d+ named area \d+ um2 box ([\d.]+) ([\d.]+) ([\d.]+) ([\d.]+)", open(sys.argv[4]).read()):
        boxes[m.group(1)] = [float(m.group(i)) for i in range(2, 6)]
rows = list(csv.DictReader(open(f"{d}/placed.csv")))
def grp(n):
    m = re.match(r"u_u_strip_u_strip_g_zn_(\d)_u_zn[./]", n)
    if m: return "zn" + m.group(1)
    if n.startswith("u_u_strip_u_strip_u_ctl.g_tc_faces") : return "ctl faces"
    if n.startswith("u_u_strip_u_strip_u_ctl"): return "ctl"
    return "other"
cols = {"zn0": "#4c78a8", "zn1": "#f58518", "zn2": "#54a24b", "zn3": "#b279a2", "ctl": "#e45756", "ctl faces": "#9d755d", "other": "#bab0ac"}
fig, ax = plt.subplots(figsize=(11, 10.5))
oth = [r for r in rows if r["kind"] in ("std", "buf")]
ax.scatter([float(r["x"]) for r in oth], [float(r["y"]) for r in oth], s=0.04, c="#dddddd", rasterized=True)
stats = {}
for g, c in cols.items():
    ff = [r for r in rows if r["kind"] == "ff" and grp(r["name"]) == g]
    xs = [float(r["x"]) for r in ff]; ys = [float(r["y"]) for r in ff]
    ax.scatter(xs, ys, s=0.2, c=c, label=f"{g} flops ({len(ff)})", rasterized=True)
    if g in boxes and ff:
        x0, y0, x1, y1 = boxes[g]
        inside = sum(1 for x, y in zip(xs, ys) if x0 - 1 <= x <= x1 + 1 and y0 - 1 <= y <= y1 + 1)
        stats[g] = dict(flops=len(ff), in_box=round(inside / len(ff), 4), cx=round(st.median(xs), 1), cy=round(st.median(ys), 1))
for g, (x0, y0, x1, y1) in boxes.items():
    ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fill=False, ec=cols.get(g, "k"), lw=1.5, ls="--"))
    ax.text(x0 + 1, y1 - 4, g, fontsize=10, color=cols.get(g, "k"), weight="bold")
wd = [r for r in rows if "u_wd" in r["name"] and r["kind"] == "ff"]
for z in range(4):
    p = [r for r in wd if f"g_zn_{z}_u_zn" in r["name"]]
    ax.scatter([float(r["x"]) for r in p], [float(r["y"]) for r in p], marker="^", s=18, c="k")
    stats.setdefault(f"zn{z}", {})["wdec_ff"] = len(p)
    if p:
        x0, y0, x1, y1 = boxes[f"zn{z}"]
        stats[f"zn{z}"]["wdec_in_box"] = sum(1 for r in p if x0 - 1 <= float(r["x"]) <= x1 + 1 and y0 - 1 <= float(r["y"]) <= y1 + 1)
ax.scatter([], [], marker="^", c="k", label=f"zone u_wd kt/ke/lo regs ({len(wd)})")
ax.set_xlim(0, W); ax.set_ylim(0, H); ax.set_aspect("equal"); ax.legend(fontsize=7, markerscale=8, loc="lower right")
ax.set_title("kv3_astk W2r 3_place: zone flops by colour, dashed = GPL zone regions (released before DPL), ^ = per-zone wdec regs", fontsize=9)
fig.tight_layout(); fig.savefig(out, dpi=100)
json.dump(stats, open(out + ".json", "w"), indent=1)
print(json.dumps(stats))
