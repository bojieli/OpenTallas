#!/usr/bin/env python3
"""Render iqf__t1 outline + landing bands (ring_ff form) + top-face clock pins + collector relays; zoom of the band strip
with the fill (rows used / band rows, worst tap phase) from iqf_ringff_fit_1029.py.  usage: PLAN FIT_JSON OUT_PNG"""
import json, sys
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
P = json.load(open(sys.argv[1])); fit = json.load(open(sys.argv[2])); t = P["partition_types"]["iqf__t1"]
W, H = t["outline_um"]; lc = t["clock"]["landing_contract"]; bands = lc["bands"]
fig, (a, z) = plt.subplots(2, 1, figsize=(13, 13), gridspec_kw=dict(height_ratios=[3, 1.3]))
for ax, (x0, x1, y0, y1) in ((a, (-40, W + 40, -40, H + 40)), (z, (0, 1000, 1170, 1230))):
    ax.add_patch(Rectangle((0, 0), W, H, fill=False, lw=2, ec="k"))
    for bus, b in bands.items():
        r = b["rect_um"]; f = fit[bus]
        ax.add_patch(Rectangle((r[0], r[1]), r[2] - r[0], r[3] - r[1], fc="#4c8bd6", alpha=.35, ec="#1f4e8c", lw=1.5))
        used = f["worst_phase_rows_used"] / f["band_rows"]
        ax.add_patch(Rectangle((r[0], r[1]), r[2] - r[0], (r[3] - r[1]) * used, fc="none", ec="#c0392b", lw=1, ls="--"))
        if ax is z:
            ax.text((r[0] + r[2]) / 2, r[1] - 4, f"{bus} ring_place={b.get('ring_place','all')}\n{f['ring_flops']} flops FIRM, need {f['ff_ratio']:.2f}x band, "
                    f"spread {f['spread']:.2f}\nrows {f['worst_phase_rows_used']}/{f['band_rows']} (worst tap phase)", ha="center", va="top", fontsize=8)
    for p in lc["pins"]:
        x, y = p["xy_um"]; ax.plot(x, y, "v" if p["dir"] == "in" else "^", ms=7, color="#27ae60" if p["dir"] == "in" else "#8e44ad")
        if ax is z: ax.text(x, y + 2, p["name"].replace("fclk_", ""), rotation=60, fontsize=7, ha="left", va="bottom")
    tr = lc.get("collector_tree") or {}
    for r in tr.get("relays", []): ax.plot(*r["xy"], "s", ms=4, color="#e67e22")
    ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); ax.set_aspect("equal" if ax is a else "auto"); ax.grid(alpha=.2)
a.set_title(f"iqf__t1 outline {W} x {H} um: landing bands (blue, rects unchanged; red dashed = rows used by FIRM ring flops), "
            f"clock pins (green in / purple out), reset relays (orange)", fontsize=9)
z.set_title("zoom: top-face band strip (x 0..1000, y 1170..1230)", fontsize=9)
plt.tight_layout(); plt.savefig(sys.argv[3], dpi=110)
