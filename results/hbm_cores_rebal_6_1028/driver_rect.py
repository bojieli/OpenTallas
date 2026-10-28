#!/usr/bin/env python3
"""HBM-CORES-REBAL-6 (die-local estimate + values): plan-fixed SRAM arrays for lanes_plain / programme_store that
obey the existing kit_contract macro rules (>= 10.8 um vertical channels incl. the fence edges, one >= 10.8 interior
horizontal channel per column, 4.32 halo), ignoring the 12.8b island grid; then for every island whose 8.64 rect
meets a macro + halo, the nearest legal driver_rect (box D x D, centre >= D/2 clear of every macro + halo, inside the
fence) for master_plan.pushdown_island(driver_rect=...) (REBAL-5 7cc88eeba0).  Detour = 2 x Manhattan.
  driver_rect.py CFG.json OUT.json OUT.png"""
import json, sys
import numpy as np

MIN, HALO, D = 10.8, 4.32, 2.16
ICH = None  # interior horizontal channel width (>= MIN), from cfg
cfg = json.load(open(sys.argv[1]))
ICH = max(MIN, cfg.get("interior_channel_um", MIN))
fx0, fy0, fx1, fy1 = cfg["fence"]
w, h = cfg["macro_wh"]
ncol, nrow = cfg["cols"], cfg["rows"]
# columns: first at the fence left + MIN... the fence is already >= MIN inside the core (checked below); col0 left,
# last col right, middle columns spread evenly in the remainder
X = cfg.get("col_x0")
if X is None:
    left, right = fx0 + cfg.get("edge", 0.0), fx1 - cfg.get("edge", 0.0) - w
    X = [left + (right - left) * i / (ncol - 1) for i in range(ncol)]
gaps = [X[i + 1] - X[i] - w for i in range(ncol - 1)]
assert min(gaps) >= MIN - 1e-6, gaps
# rows: stacked at 2*HALO pitch, one interior MIN channel at the row index cfg["chan_after"][col]
slots = []
for c, x in enumerate(X):
    ca = cfg["chan_after"][c]
    tot = nrow * h + (nrow - 2) * 2 * HALO + ICH
    y = fy0 + HALO + ((fy1 - fy0 - 2 * HALO) - tot) / 2 if "row_y0" not in cfg else cfg["row_y0"][c]
    for r in range(nrow):
        slots.append((c, r, x, y))
        y += h + (ICH if r == ca else 2 * HALO)
    assert y - (ICH if nrow - 1 == ca else 2 * HALO) <= fy1 - HALO + 1e-6, (c, y)
empty = cfg.get("empty_slots", [])
used = [s for s in slots if [s[0], s[1]] not in empty]
assert len(used) == cfg["n_macros"], (len(used), cfg["n_macros"])
# instance assignment: RTLMP order (columns by x rank, rows by y) -> slot order (column-major)
mp = json.load(open(cfg["rtlmp"]))["macro_placement"]
mp = sorted(mp, key=lambda m: m["xy_um"][0])
per = [len([s for s in used if s[0] == c]) for c in range(ncol)]
assign, k = [], 0
for c in range(ncol):
    col = sorted(mp[k:k + per[c]], key=lambda m: m["xy_um"][1]); k += per[c]
    cs = [s for s in used if s[0] == c]
    for m, s in zip(col, cs):
        assign.append(dict(inst=m["inst"], orient=m["orient"], origin_um=[round(s[2], 3), round(s[3], 3)],
                           rtlmp_um=m["xy_um"], move_um=round(abs(s[2] - m["xy_um"][0]) + abs(s[3] - m["xy_um"][1]), 3)))
bad = [(a["origin_um"][0] - HALO, a["origin_um"][1] - HALO, a["origin_um"][0] + w + HALO, a["origin_um"][1] + h + HALO)
       for a in assign]
# nearest legal driver centre on a 0.054 grid
g = 0.054
xs = np.arange(fx0 + D / 2, fx1 - D / 2 + 1e-9, g); ys = np.arange(fy0 + D / 2, fy1 - D / 2 + 1e-9, g)
ok = np.ones((len(ys), len(xs)), bool)
for x0, y0, x1, y1 in bad:
    ok[np.ix_((ys > y0 - D / 2) & (ys < y1 + D / 2), (xs > x0 - D / 2) & (xs < x1 + D / 2))] = False
isl = {}
for c in json.load(open(cfg["infra"]))["cells"]:
    isl.setdefault(c["name"].split("_")[1], tuple(c["rect_um"]))
out = []
for name, r in sorted(isl.items(), key=lambda t: int(t[0][3:])):
    cx, cy = (r[0] + r[2]) / 2, (r[1] + r[3]) / 2
    hit = any(r[0] < b[2] and r[2] > b[0] and r[1] < b[3] and r[3] > b[1] for b in bad)
    if not hit:
        out.append(dict(island=name, rect_um=list(r), centre_um=[cx, cy], overlaps_macro=False, driver_rect_um=None, detour_um=0.0))
        continue
    yy, xx = np.nonzero(ok)
    dist = np.abs(xs[xx] - cx) + np.abs(ys[yy] - cy)
    i = int(np.argmin(dist)); dx, dy = float(xs[xx[i]]), float(ys[yy[i]])
    out.append(dict(island=name, rect_um=list(r), centre_um=[cx, cy], overlaps_macro=True,
                    driver_rect_um=[round(dx - D / 2, 3), round(dy - D / 2, 3), round(dx + D / 2, 3), round(dy + D / 2, 3)],
                    detour_um=round(2 * float(dist[i]), 3)))
res = dict(core=cfg["core"], interior_channel_um=ICH, fence=cfg["fence"], macro_wh=[w, h], halo=HALO, min_channel=MIN, driver_box_um=D,
           col_x0=[round(x, 3) for x in X], col_gaps_um=[round(v, 3) for v in gaps], empty_slots=empty,
           macro_placement=assign, max_move_um=max(a["move_um"] for a in assign),
           islands=out, max_detour_um=max(o["detour_um"] for o in out),
           basis="plan geometry only (UNCHECKED QoR): macro+halo clear, kit_contract channel rules by construction")
json.dump(res, open(sys.argv[2], "w"), indent=1)
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
f, ax = plt.subplots(figsize=(8, 8 * (fy1 - fy0 + 30) / (fx1 - fx0 + 30)))
ax.add_patch(Rectangle((fx0, fy0), fx1 - fx0, fy1 - fy0, fill=False, ec="k", lw=1))
for a in assign:
    x, y = a["origin_um"]
    ax.add_patch(Rectangle((x - HALO, y - HALO), w + 2 * HALO, h + 2 * HALO, fc="#f3d9a0", ec="none"))
    ax.add_patch(Rectangle((x, y), w, h, fc="#c08a2a", ec="k", lw=.4))
for o in out:
    r = o["rect_um"]
    ax.add_patch(Rectangle((r[0], r[1]), r[2] - r[0], r[3] - r[1], fill=False, ec="b", lw=1.2))
    if o["driver_rect_um"]:
        d = o["driver_rect_um"]
        ax.add_patch(Rectangle((d[0], d[1]), d[2] - d[0], d[3] - d[1], fc="r", ec="r"))
        ax.plot([o["centre_um"][0], (d[0] + d[2]) / 2], [o["centre_um"][1], (d[1] + d[3]) / 2], "r-", lw=1)
    ax.text(r[2] + 1, r[3] + 1, o["island"], fontsize=6, color="b")
ax.set_xlim(fx0 - 15, fx1 + 15); ax.set_ylim(fy0 - 15, fy1 + 15); ax.set_aspect("equal")
ax.set_title(f"{cfg['core']}: {len(assign)} SRAM, gaps {min(gaps):.1f}-{max(gaps):.1f} um; island (blue) -> driver_rect (red), max detour {res['max_detour_um']:.1f} um", fontsize=8)
f.savefig(sys.argv[3], dpi=130, bbox_inches="tight")
print(cfg["core"], "max_move", res["max_move_um"], "max_detour", res["max_detour_um"],
      [(o["island"], o["detour_um"]) for o in out if o["overlaps_macro"]])
