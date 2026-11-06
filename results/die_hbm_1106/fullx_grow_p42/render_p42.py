#!/usr/bin/env python3
"""part 42 plan-time GEOM render: q_su00 / q_su10 around u_su_Q*_lane_exp0 (__l grown E, __s shifted E), base vs new.
    render_p42.py BASE_DIR NEW_DIR OUT.png"""
import json, sys
from pathlib import Path
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
b, n = Path(sys.argv[1]), Path(sys.argv[2])
fig, axs = plt.subplots(2, 2, figsize=(22, 14), dpi=110)
for row, (tn, q, zoom) in enumerate((("q_su00", "0", (-10, 860, 720, 1180)), ("q_su10", "1", (480, 470, 1380, 790)))):
    for col, (lab, d) in enumerate((("base", b), ("part42", n))):
        ax = axs[row][col]; T = json.loads((d / "die_plan.json").read_text())["partition_types"][tn]
        for h in T["hard_cores"]:
            (x, y), (w, hh) = h["origin_um"], h["outline_um"]
            me = h["inst"].startswith("u_su_Q%s_lane_exp0__" % q)
            c = "tab:red" if me else "tab:blue"
            ax.add_patch(Rectangle((x, y), w, hh, fill=True, alpha=0.18, color=c)); ax.add_patch(Rectangle((x, y), w, hh, fill=False, lw=0.8, color=c))
            if zoom[0] < x + w / 2 < zoom[2] and zoom[1] < y + hh / 2 < zoom[3]:
                ax.text(x + w / 2, y + hh / 2, "%s\n%s\nx %.2f-%.2f  %gx%g %s" % (h["inst"], h["module"][-26:], x, x + w, w, hh, h.get("orient", "R0")),
                        ha="center", va="center", fontsize=6)
            if me:
                pins = json.loads((d / h["pins_file"]).read_text()); mx = h.get("orient") == "MX"
                for p in pins:
                    nm = p.get("name") or p.get("bus", "")
                    col_ = "green" if ("sx_" in nm or nm.startswith(("R[", "y_", "v", "fault", "ci_sfu", "fn", "r["))) else "gray"
                    ax.plot(x + p["x"], y + (hh - p["y"] if mx else p["y"]), ".", ms=0.6, color=col_)
        for tp in T["clock"]["taps"]:
            ax.plot(*tp["xy"], "k+", ms=8)
        for s in T.get("internal_stations") or []:
            for r in s.get("regs_um") or []:
                ax.plot(*r, "s", ms=2.5, color="purple")
        ax.set_aspect("equal"); ax.set_xlim(zoom[0], zoom[2]); ax.set_ylim(zoom[1], zoom[3])
        ax.set_title("%s %s: red = lane_exp0 __l (full_x) + __s (sfu_s); + taps, purple station regs, green seam pins" % (tn, lab), fontsize=9)
fig.tight_layout(); fig.savefig(sys.argv[3]); print("render", sys.argv[3])
