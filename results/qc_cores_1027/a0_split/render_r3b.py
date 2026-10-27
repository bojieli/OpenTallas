#!/usr/bin/env python3
"""QC-CORES-2 A0-CLK-R3b render: die-coordinate panels of chosen A0 instances with the R22 mesh straps (grey) and the R3b drop
straps (pink M9 / blue M8), islands (red) and their drop crossings (black dot).  usage: render_r3b.py R3B.json FLOORPLAN R2_D43 OUT.png"""
import json, sys
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
R, FP, R2, OUT = sys.argv[1:5]
d = json.load(open(R)); fp = json.load(open(FP)); r2 = json.load(open(R2))
L = d["lattices"]["R22_d43_PROVISIONAL"]; per = {q["n"]: q for q in L["per_instance"]}
CW, CH, ISL = 457.92, 1157.76, 4.32
sl = [q["n"] for q in L["strapless_under_r22"]]
nk_norm = next(q for q in L["per_instance"] if "nk_" in q["m"] and not q["mx"] and q["r22_m9_over_core"] == 2 and 5000 < q["y0"] < 20000)
nl_mx = next(q for q in L["per_instance"] if "nl_" in q["m"] and q["mx"])
nl_r0 = next(q for q in L["per_instance"] if "nl_" in q["m"] and not q["mx"])
picks = [per["c_W5_bn_00/u_t00"], per["c_W5_tn_00/u_t00"], nk_norm, nl_mx, nl_r0]
fig, axs = plt.subplots(1, len(picks), figsize=(4.0 * len(picks), 10.5))
for ax, q in zip(axs, picks):
    x0, y0, mx = q["x0"], q["y0"], q["mx"]
    core = "nk" if "nk_" in q["m"] else "nl"
    Y = lambda v: y0 + (CH - v if mx else v)
    ax.add_patch(Rectangle((x0, y0), CW, CH, fill=False, lw=1.6, ec="k"))
    for c in fp[core]["hard_children"]:
        (a, b), (w, h) = c["at"], c["size_um"]
        k = c["view"]; col = "#9ecae1" if "romleaf" in k else "#fdae6b" if "node" in k else "#a1d99b"
        ax.add_patch(Rectangle((x0 + a, min(Y(b), Y(b + h))), w, h, fc=col, ec="#555", lw=0.5))
    for x in r2["xs"]:
        if x0 - 120 <= x <= x0 + CW + 120: ax.axvline(x, color="#999", lw=0.8, zorder=1)
    for y in r2["ys"]:
        if y0 - 60 <= y <= y0 + CH + 60: ax.axhline(y, color="#999", lw=0.8, zorder=1)
    for u in d["type_lattice"]["m9_u"]: ax.axvline(x0 + u, color="#e08", lw=0.7, ls=(0, (5, 3)), zorder=2)
    for v in d["type_lattice"]["m8_v"]: ax.axhline(Y(v), color="#08c", lw=0.7, ls=(0, (5, 3)), zorder=2)
    for n, t in d["islands"].items():
        cx, cy = t["centre"]; ux, uy = t["drop_core_frame"]
        ax.add_patch(Rectangle((x0 + cx - ISL, Y(cy) - ISL), 2 * ISL, 2 * ISL, fc="#c00", ec="k", lw=0.5, zorder=4))
        ax.plot(x0 + ux, Y(uy), "k.", ms=3, zorder=5)
    ax.set_xlim(x0 - 120, x0 + CW + 120); ax.set_ylim(y0 - 60, y0 + CH + 60); ax.set_aspect("equal")
    ax.tick_params(labelsize=6)
    ax.set_title(f"{q['n']} ({core.upper()}, {'MX' if mx else 'R0'})\nx0 {x0} y0 {y0}\nR22 M9 over core: {q['r22_m9_over_core']}; "
                 f"R22 crossings at islands: {q['r22_crossings_at_islands']}\nR3b drop crossings: {q['r3b_crossings']}/22"
                 + ("\nSTRAP-LESS under R22" if q["n"] in sl else ""), fontsize=7)
fig.suptitle("A0-CLK-R3b (QC-CORES-2 10-27): grey = R22 mesh straps (PROVISIONAL lattice); pink/blue dashed = R3b A0 drop straps "
             "(M9 x0+U / M8 y0+V, VSS lanes 8.64k); red = 22 islands; dot = drop crossing (stacked via M9->M5, die stub 0)", fontsize=8)
fig.tight_layout(); fig.savefig(OUT, dpi=105)
