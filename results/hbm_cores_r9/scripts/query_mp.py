#!/usr/bin/env python3
"""HBM-CORES-R9: plan-computed explicit macro placement for ot_hbm_idx_query_static (170.64 x 164.16, core 4.32..166.32 x
4.32..159.84; pins E 1056 / S 569 (x 8.8-161.9) / W 8 clocks+reset at y>142 / N 0).
GEOM-REVIEW-25 07:31/07:52 FAIL STRUCTURAL of the k2 auto (RTL-MP) placement: SE 3-SRAM abutted stack 17 um from the
1056-pin E face + 8.6-um gcode0/3 gap -> 7,851 capacity-0 gcells, overflow 13,484 @50 it.
Fix (COORD 07:09 SRAM-stack ruling; GEOM fix "move the stack W, H channels"): 5 x ot_sram_1r1w_32x128_m1 (51.408 x 20.79,
pins M4 on the W/E edges only) on the pinless N edge + the nearly pinless W side, L-shape:
  N row (y 134.73, 4.32 below the core top): gcode[0] x 25.92, gcode[3] x 88.128 -> 10.8-um V channel between them,
  E end 139.536 (+halo 143.856) leaves 22.5 um to the E pin face;
  W column (x 25.92) below: gcode[1] y 103.14, scmem y 71.55 (beside the clock entry y 82), gcode[2] y 39.96;
  every interior channel 10.8 um (2 x 4.32 halo + 8 rows, QUAD-6 G0C proposal); W band 17.28 um outside the halo;
  bottom 35.6 um free for the 569-pin S face; column E edge + halo 81.648 < clock island 82.08.
usage: query_mp.py OUT.tcl OUT.json [render.png]"""
import json, sys
MW, MH, CH = 51.408, 20.79, 10.8
X0, YN = 25.92, 134.73
slots = [("core.gcode\\[0\\].mem", X0, YN), ("core.gcode\\[3\\].mem", round(X0 + MW + CH, 4), YN)]
y = YN
for n in ["core.gcode\\[1\\].mem", "core.scmem", "core.gcode\\[2\\].mem"]:
    y = round(y - CH - MH, 4); slots.append((n, X0, y))
core = (4.32, 4.32, 166.32, 159.84)
isl = (82.08, 77.76, 90.72, 86.4)
mp, rects = [], []
for n, x, y in slots:
    assert abs((x - 4.32) / 0.054 - round((x - 4.32) / 0.054)) < 1e-6 and abs((y - 4.32) / 0.27 - round((y - 4.32) / 0.27)) < 1e-6, n
    assert core[0] <= x and x + MW <= core[2] and core[1] <= y and y + MH <= core[3], n
    r = (x, y, x + MW, y + MH); rects.append(r)
    h = (r[0] - 4.32, r[1] - 4.32, r[2] + 4.32, r[3] + 4.32)
    assert h[2] <= isl[0] or isl[2] <= h[0] or h[3] <= isl[1] or isl[3] <= h[1], ("island under halo", n)
    mp.append(dict(k="u_fcore." + n, macro="ot_sram_1r1w_32x128_m1", origin_um=[x, y], orient="R0"))
gaps = []
for i in range(len(rects)):
    for j in range(i + 1, len(rects)):
        a, b = rects[i], rects[j]
        gx = max(b[0] - a[2], a[0] - b[2]); gy = max(b[1] - a[3], a[1] - b[3])
        g = max(gx, gy); assert g >= CH - 1e-6, (i, j, g); gaps.append(round(g, 3))
with open(sys.argv[1], "w") as f:
    for m in mp:
        f.write("place_macro -macro_name {%s} -location {%g %g} -orientation R0 -exact\n" % (m["k"], *m["origin_um"]))
json.dump(dict(schema="opentallas.macro_placement.v1", design="ot_hbm_idx_query_static", outline_um=[170.64, 164.16],
               rule=__doc__.split("usage")[0].strip(), macro_placement=mp, min_channel_um=min(gaps),
               w_band_um=round(X0 - 8.64, 3), s_band_um=round(min(r[1] for r in rects) - 4.32, 3)), open(sys.argv[2], "w"), indent=1)
print("macros", len(mp), "min channel", min(gaps), "S band", round(min(r[1] for r in rects) - 4.32, 3))
if len(sys.argv) > 3:
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt; from matplotlib.patches import Rectangle
    f, ax = plt.subplots(figsize=(7, 6.8)); ax.add_patch(Rectangle((0, 0), 170.64, 164.16, fill=False))
    ax.add_patch(Rectangle(core[:2], core[2] - core[0], core[3] - core[1], fill=False, ls=":"))
    for m, r in zip(mp, rects):
        ax.add_patch(Rectangle(r[:2], MW, MH, fc="#c8c8e8", ec="k")); ax.text(r[0] + 1, r[1] + 1, m["k"].split(".", 1)[1].replace("\\", ""), fontsize=7)
        ax.add_patch(Rectangle((r[0] - 4.32, r[1] - 4.32), MW + 8.64, MH + 8.64, fill=False, ls="--", lw=0.5))
    ax.add_patch(Rectangle(isl[:2], 8.64, 8.64, fc="red"))
    ax.plot([170.64, 170.64], [8, 156], "g", lw=3); ax.plot([8.8, 161.9], [0, 0], "g", lw=3)
    ax.set_xlim(-5, 176); ax.set_ylim(-5, 170); ax.set_aspect("equal"); ax.set_title("query_static R9 plan macro placement (pins green)")
    f.savefig(sys.argv[3], dpi=110)
