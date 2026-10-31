#!/usr/bin/env python3
"""DIE-HBM-44 review render: d41v vs d44c on the changed seams (L206/L206m, L6b/L6bm, L744/L744m): partitions, hard
cores, lane polyline FF->seam pin->FF (red = d41v, green = d44c)."""
import sys, json
from pathlib import Path
sys.path.insert(0, "/srv/opentallas-scratch2/claude/wt/die-hbm-42/tools/die_plan")
import check as C
S = C.S
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
base, new, png = sys.argv[1:4]
def load(f):
    raw = json.load(open(f)); return S.Plan(raw, Path(f))
PB, PN = load(base), load(new)
views = [("L206 NW su01|spu0", ["L206"], (5200, 6700, 11200, 12200)), ("L206m NE", ["L206m"], (21700, 23200, 11200, 12200)),
         ("L6b NW su31|b110", ["L6b"], (10800, 12100, 5100, 6200)), ("L6bm NE", ["L6bm"], (16300, 17600, 5100, 6200)),
         ("L744 NW b101|hub", ["L744"], (12600, 13400, 5800, 6400)), ("L744m NE b101|hub", ["L744m"], (15000, 15800, 5800, 6400))]
fig, axs = plt.subplots(2, 3, figsize=(21, 13))
for ax, (title, lanes, (x0, x1, y0, y1)) in zip(axs.flat, views):
    for pn in PN.parts:
        r = PN.rect(pn); ax.add_patch(Rectangle((r[0], r[1]), r[2]-r[0], r[3]-r[1], fill=False, lw=1.2, ec="k"))
        if x0 < (r[0]+r[2])/2 < x1 and y0 < (r[1]+r[3])/2 < y1: ax.text((r[0]+r[2])/2, (r[1]+r[3])/2, pn, fontsize=8)
        for bx in S.placed_macro_boxes(PN.ptype(pn), halo=0).values():
            a, b = PN.to_die(pn, (bx[0], bx[1])), PN.to_die(pn, (bx[2], bx[3]))
            ax.add_patch(Rectangle((min(a[0], b[0]), min(a[1], b[1])), abs(b[0]-a[0]), abs(b[1]-a[1]), fc="0.85", ec="0.6", lw=0.3))
    for P, col, lab in ((PB, "r", "d41v"), (PN, "g", "d44c")):
        for lid in lanes:
            if lid not in P.lanes: continue
            pts, regs, xs = C.lane_geometry(P, lid)
            seq = [regs[0]]; i = 1
            for part, slot, a, b in P.lane_crossings(lid):
                k = int((P.slot(part, slot) or {}).get("stations", 1))
                seq.append(P.port_point(a)); seq += regs[i:i+k]; i += k; seq.append(P.port_point(b))
            seq.append(regs[-1])
            ax.plot([p[0] for p in seq], [p[1] for p in seq], col + "-", lw=1.5, label=f"{lab} {lid} max hop {max(C.lane_pin_hops(P, lid, regs)):.0f}")
            ax.plot([p[0] for p in regs], [p[1] for p in regs], col + "o", ms=4)
            for _, _, a, b in P.lane_crossings(lid):
                for q in (a, b):
                    pp = P.port_point(q); ax.plot(pp[0], pp[1], col + "s", ms=7, mfc="none")
            if not P.lane_crossings(lid):
                pp = P.port_point(P.lanes[lid]["ports"][0]); ax.plot(pp[0], pp[1], col + "s", ms=9, mfc="none")
    if "L744m" in lanes:
        for P, col in ((PB, "r"), (PN, "g")):
            w = P.ports["L12m_1"]["window_um"] if "L12m_1" in P.ports else None
            if w: ax.plot(w, [6065.28, 6065.28], "b-", lw=4, label="L12m_1 window")
    ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); ax.set_aspect("equal"); ax.set_title(title); ax.legend(fontsize=7, loc="upper left")
plt.tight_layout(); plt.savefig(png, dpi=80)
