"""SC-REFLOOR-1: render route_supply rV/rH maps of an sc type with core, ft regs, landing bands.
usage: sc_map.py PLAN.json NPZ TYPE OUT.png [title]"""
import json, sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
plan, npz, tn, out = sys.argv[1:5]
title = sys.argv[5] if len(sys.argv) > 5 else tn
p = json.load(open(plan))
t = p["partition_types"][tn]
W, H = t["outline_um"]
z = np.load(npz)
fig, axs = plt.subplots(1, 2, figsize=(11, 12))
col = {"N>S": "tab:blue", "S>N": "tab:cyan", "W>E": "tab:red", "E>W": "tab:orange", "W>N": "tab:purple",
       "N>W": "tab:purple", "E>N": "tab:pink", "S>E": "tab:brown"}
for ax, key in zip(axs, ("rV", "rH")):
    R = z[key]
    b = W / R.shape[1]
    im = ax.imshow(R, origin="lower", extent=[0, R.shape[1] * b, 0, R.shape[0] * b], vmin=0, vmax=1.6, cmap="RdYlGn_r")
    for c in t.get("hard_cores") or []:
        (x, y), (w, h) = c["origin_um"], c["outline_um"]
        ax.add_patch(Rectangle((x, y), w, h, fill=False, ec="k", lw=2))
    for bn, bd in (((t.get("clock") or {}).get("landing_contract") or {}).get("bands") or {}).items():
        r = bd.get("rect_um")
        if r:
            ax.add_patch(Rectangle((r[0], r[1]), r[2] - r[0], r[3] - r[1], fill=False, ec="m", lw=0.8, ls="--"))
    for s in t["ft_slots"]:
        k = s["in_face"] + ">" + s["out_face"]
        regs = s.get("regs_um") or []
        if regs:
            xs = [r[0] for r in regs]; ys = [r[1] for r in regs]
            ax.plot(xs, ys, "-o", color=col.get(k, "k"), lw=1.2, ms=3)
            ax.text(xs[-1], ys[-1], s["name"], fontsize=6)
        ow = s.get("out_window_um")
        if ow:
            f = s["out_face"]
            if f in ("N", "S"):
                yy = H if f == "N" else 0
                ax.plot(ow, [yy, yy], color=col.get(k, "k"), lw=4)
            else:
                xx = W if f == "E" else 0
                ax.plot([xx, xx], ow, color=col.get(k, "k"), lw=4)
    ax.set_xlim(0, W); ax.set_ylim(0, H); ax.set_aspect("equal")
    ax.set_title(f"{key} {title}", fontsize=9)
    fig.colorbar(im, ax=ax, fraction=0.03)
plt.tight_layout()
plt.savefig(out, dpi=90)
print("wrote", out)
