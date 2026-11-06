import json, sys, re
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
plan, pins_cl, out = sys.argv[1], sys.argv[2], sys.argv[3]
P = json.load(open(plan))
names = ["cbn_q00__cl622f65d2", "cbn_q00__cldbcda913"]
fig, axs = plt.subplots(1, 4, figsize=(22, 14), gridspec_kw=dict(width_ratios=[1, 1, 1.4, 1.4]))
pp = json.load(open(pins_cl))["pins"]
col = {"na_i00": "tab:red", "rsf_i": "tab:orange", "nb_i00": "tab:purple", "bc_i00": "tab:green", "bc_i10": "tab:olive"}
for ax, tn in zip(axs[:2], names):
    t = P["partition_types"][tn]; X, Y = t["outline_um"]
    ax.add_patch(Rectangle((0, 0), X, Y, fill=False, lw=1))
    for h in t["hard_cores"]:
        (x, y), (w, hh) = h["origin_um"], h["outline_um"]
        c = "lightgray" if h["module"].startswith("qfd") else col.get(h["inst"][3:], "k")
        ax.add_patch(Rectangle((x, y), w, hh, fc=c, ec="k", lw=.5, alpha=.8))
        ax.text(x + w / 2, y + hh / 2, h["inst"], fontsize=6, ha="center", va="center")
    for k, v in t["clock"]["landing_contract"]["bands"].items():
        if not v.get("hard_core") and "rect_um" in v:
            r = v["rect_um"]; ax.add_patch(Rectangle((r[0], r[1]), r[2] - r[0], r[3] - r[1], fc="cyan", ec="b", lw=.5))
    ax.set_xlim(-20, X + 20); ax.set_ylim(-20, Y + 20); ax.set_aspect("equal"); ax.set_title(tn, fontsize=9)
# zooms with type pins (cl622)
for ax, (y0, y1), tn in [(axs[2], (2440, 2535), names[0]), (axs[3], (-5, 90), names[0])]:
    t = P["partition_types"][tn]
    for h in t["hard_cores"]:
        (x, y), (w, hh) = h["origin_um"], h["outline_um"]
        c = "lightgray" if h["module"].startswith("qfd") else col.get(h["inst"][3:], "k")
        ax.add_patch(Rectangle((x, y), w, hh, fc=c, ec="k", lw=.5, alpha=.6))
        if y1 > y and y + hh > y0: ax.text(x + w / 2, max(y, y0) + 3, h["inst"] + "\n" + h["module"], fontsize=6, ha="center")
    for k, v in t["clock"]["landing_contract"]["bands"].items():
        if not v.get("hard_core") and "rect_um" in v:
            r = v["rect_um"]; ax.add_patch(Rectangle((r[0], r[1]), r[2] - r[0], r[3] - r[1], fc="cyan", ec="b", lw=.5))
    for p in pp:
        b = re.sub(r"\[\d+\]", "", p["name"])
        if y0 <= p["y"] <= y1:
            ax.plot(p["x"], p["y"], ".", ms=1.5, color=col.get(b, "k"))
    ax.axhline(2462.4 if y0 > 1000 else 77.76, color="gray", ls="--", lw=.5)
    ax.set_xlim(-5, 1240); ax.set_ylim(y0, y1); ax.set_title(f"{tn} zoom y {y0}..{y1} (pins coloured by bus, black = other)", fontsize=8)
plt.tight_layout(); plt.savefig(out, dpi=110)
