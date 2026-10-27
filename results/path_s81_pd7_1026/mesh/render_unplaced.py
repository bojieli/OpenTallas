#!/usr/bin/env python3
"""PATH-S81-PD7: render the die_clock_mesh S81 probe's STRUCTURAL unplaced H-tree legs over partitions + hard cores.
   render_unplaced.py PLAN DIAG.json OUT.png OUT.json   (DIAG = cells + plan-error rows dumped by the diagnostic build)"""
import json, sys
from pathlib import Path
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "tools/die_plan"))
import schema as S
raw = json.loads(Path(sys.argv[1]).read_text()); diag = json.loads(Path(sys.argv[2]).read_text())
W, H = raw["die"]["outline_um"]; T = raw["partition_types"]
fig, ax = plt.subplots(figsize=(16, 12.5))
def tf(o, w, h, x0, y0, x1, y1, orient):
    if orient in ("MX", "R180"): y0, y1 = h - y1, h - y0
    if orient in ("MY", "R180"): x0, x1 = w - x1, w - x0
    return o[0] + x0, o[1] + y0, o[0] + x1, o[1] + y1
for p in raw["partitions"]:
    t = T[p["type"]]; w, h = t["outline_um"]; o = p["origin_um"]
    ax.add_patch(Rectangle(o, w, h, fill=False, lw=0.4, ec="0.5"))
    for b in S.placed_macro_boxes(t).values():
        x0, y0, x1, y1 = tf(o, w, h, *b[:4], p.get("orient", "N"))
        ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fc="#c9a227", ec="none", alpha=0.5))
C = diag["cells"]
def xy(n):
    c = C.get(n); return None if c is None else (c["x"], c["y"])
rows = [r for r in diag["rows"] if r["kind"] == "unplaced"]; legs = []
for r in rows:
    a, b = r["detail"][0], r["detail"][1]; pa, pb = xy(a), xy(b)
    legs.append(dict(drv=a, load=b, drv_xy=pa, load_xy=pb, span_um=r["detail"][3]))
    if pa and pb:
        ax.plot([pa[0], pb[0], pb[0]], [pa[1], pa[1], pb[1]], "r-", lw=1.6)
        ax.plot(*pa, "rs", ms=4); ax.plot(*pb, "bo", ms=4)
ax.set_xlim(0, W); ax.set_ylim(0, H); ax.set_aspect("equal")
ax.set_title(f"S81 die_clock_mesh 64x64 probe on PD5 composed plan: {len(rows)} STRUCTURAL unplaced H-tree legs (red L, square=driver, dot=load); gold = hard cores")
fig.savefig(sys.argv[3], dpi=110, bbox_inches="tight")
Path(sys.argv[4]).write_text(json.dumps(dict(n=len(rows), legs=legs), indent=1)); print(len(rows), "legs", sum(1 for l in legs if l["drv_xy"] and l["load_xy"]), "with xy")
