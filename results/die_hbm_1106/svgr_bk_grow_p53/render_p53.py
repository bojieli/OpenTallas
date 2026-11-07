#!/usr/bin/env python3
"""part 53 plan-time GEOM render: q_hub_nw around u_svg_Q0 (MX) and u_svg_Q2 (MY): ot_svgr_bk pair grown, base vs new.
    render_p53.py BASE_DIR NEW_DIR OUT.png"""
import json, sys
from pathlib import Path
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
b, n = Path(sys.argv[1]), Path(sys.argv[2])
fig, axs = plt.subplots(2, 2, figsize=(22, 14), dpi=110)
for row, (q, zoom) in enumerate((("0", (800, 1780, 1660, 2480)), ("2", (360, 1100, 1210, 1720)))):
    for col, (lab, d) in enumerate((("base", b), ("part53", n))):
        ax = axs[row][col]; T = json.loads((d / "die_plan.json").read_text())["partition_types"]["q_hub_nw"]
        for h in T["hard_cores"]:
            (x, y), (w, hh) = h["origin_um"], h["outline_um"]
            me = h["module"] == "ot_svgr_bk" and h["inst"].startswith("u_svg_Q%s__" % q)
            c = "tab:red" if me else "tab:blue"
            ax.add_patch(Rectangle((x, y), w, hh, fill=True, alpha=0.18, color=c)); ax.add_patch(Rectangle((x, y), w, hh, fill=False, lw=0.8, color=c))
            if zoom[0] < x + w / 2 < zoom[2] and zoom[1] < y + hh / 2 < zoom[3]:
                ax.text(x + w / 2, y + hh / 2, "%s\n%s\nx %.2f-%.2f  %gx%g %s" % (h["inst"], h["module"], x, x + w, w, hh, h.get("orient", "R0")), ha="center", va="center", fontsize=6)
            if me:
                pins = json.loads((d / h["pins_file"]).read_text()); o = h.get("orient", "R0")
                for p in pins:
                    px = x + w - p["x"] if o in ("MY", "R180") else x + p["x"]; py = y + hh - p["y"] if o in ("MX", "R180") else y + p["y"]
                    ax.plot(px, py, ".", ms=0.6, color="green" if p["name"].startswith(("in_", "cr")) else "gray")
        for tp in T["clock"]["taps"]:
            ax.plot(*tp["xy"], "k+", ms=8)
        for s in T.get("internal_stations") or []:
            for r in s.get("regs_um") or []:
                if zoom[0] < r[0] < zoom[2] and zoom[1] < r[1] < zoom[3]: ax.plot(*r, "s", ms=2.5, color="purple")
        ax.set_aspect("equal"); ax.set_xlim(zoom[0], zoom[2]); ax.set_ylim(zoom[1], zoom[3])
        ax.set_title("q_hub_nw %s u_svg_Q%s: red = ot_svgr_bk b0/b1; + taps, purple station regs, green E-face (in_*/cr) pins" % (lab, q), fontsize=9)
fig.tight_layout(); fig.savefig(sys.argv[3]); print("render", sys.argv[3])
