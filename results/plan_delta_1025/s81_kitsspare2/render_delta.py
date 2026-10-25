#!/usr/bin/env python3
"""KITS-SPARE-2 S81 delta render: BEFORE | AFTER per changed type (outline, hard cores, core taps, ft bit sites, taps)."""
import json, sys
from pathlib import Path
sys.path.insert(0, "tools/die_plan")
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import schema as S

base, after, out = sys.argv[1], sys.argv[2], Path(sys.argv[3]); out.mkdir(parents=True, exist_ok=True)
PB, PA = S.Plan(json.load(open(base))), S.Plan(json.load(open(after)))
TYPES = ["bk_sel__t2", "gunit__t1", "dsdv_slice_c3x_C__t1", "slice_station__t23", "slice_station__t46"]

def panel(ax, P, tn, title):
    t = P.types[tn]; w, h = t["outline_um"]
    ax.add_patch(Rectangle((0, 0), w, h, fill=False, lw=1.2))
    for c in t.get("hard_cores", []):
        (x, y), (cw, ch) = c["origin_um"], c["outline_um"]
        hl = c["module"] in ("dsdv_bksel_c", "dsdv_gunit_l5", "ot_s81sl_xrt3")
        ax.add_patch(Rectangle((x, y), cw, ch, color="#f4a6a6" if hl else "0.8", lw=0))
        ax.text(x + cw / 2, y + ch / 2, c["module"].replace("ot_s81sl_", "").replace("dsdv_", ""), fontsize=6, ha="center")
        if c["module"] == "ot_s81sl_xrt3" and c.get("pins_file"):
            pins = json.load(open("physical/die_plan/s81/" + c["pins_file"]))["pins"]
            col = {"M3": "#1f77b4", "M4": "#2ca02c", "M5": "#9467bd", "M6": "#d62728"}
            for p in pins[::7]:
                py = ch - p["y"] if c.get("orient") == "MX" else p["y"]
                ax.plot(x + p["x"], y + py, ".", ms=0.6, color=col.get(p["layer"], "k"))
    for s in t.get("ft_slots", []):
        for bank in s.get("bit_sites_um", []):
            xs = [b[0] for b in bank]; ys = [b[1] for b in bank]
            ax.plot(xs, ys, ".", ms=0.5, color="orange")
        r = s.get("regs_um")
        if r:
            ax.plot([q[0] for q in r], [q[1] for q in r], "-", lw=0.5, color="orange")
    try:
        for n, x, y in S.tap_grid(P, tn):
            ax.plot(x, y, "bx", ms=6, mew=1.5)
    except Exception as e:
        ax.text(5, 5, f"tap_grid: {e}", fontsize=5)
    for n, x, y, tp in S.core_taps(P, tn):
        ax.plot(x, y, "r*", ms=9)
        ax.annotate(f"{tp['name'].split('.')[-1]} {tp.get('insertion_ps',0):.0f}ps", (x, y), fontsize=5, color="r")
    ax.set_xlim(-20, w + 20); ax.set_ylim(-20, h + 20); ax.set_aspect("equal"); ax.set_title(title, fontsize=8)

for tn in TYPES:
    fig, axs = plt.subplots(1, 2, figsize=(16, 7))
    panel(axs[0], PB, tn, f"{tn} BEFORE (main)"); panel(axs[1], PA, tn, f"{tn} AFTER (delta)  x=clock taps  *=early core tap")
    fig.tight_layout(); fig.savefig(out / f"{tn}.png", dpi=130); plt.close(fig)
print("ok")
