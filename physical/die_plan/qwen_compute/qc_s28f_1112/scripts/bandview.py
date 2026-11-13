"""QC-S28-F before/after band + tap view: cores, all landing bands (monitor bands red), monitor status pins, density
taps (fw types: tap points sized by kit load).  usage: bandview.py BASE AFTER OUTDIR TYPE..."""
import json, sys
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
B, A, OUT = sys.argv[1:4]; TYPES = sys.argv[4:]
P = [json.load(open(B)), json.load(open(A))]
for tn in TYPES:
    fig, axs = plt.subplots(1, 2, figsize=(12, 13))
    for ax, raw, lab in zip(axs, P, ("before s28", "after s28f")):
        t = raw["partition_types"][tn]; W, H = t["outline_um"]; ck = t["clock"]; lc = ck["landing_contract"]
        ax.add_patch(Rectangle((0, 0), W, H, fill=False, ec="k"))
        for h in t["hard_cores"]:
            (x, y), (w, hh) = h["origin_um"], h["outline_um"]
            ax.add_patch(Rectangle((x, y), w, hh, fc="#cfd8e3", ec="#556", lw=.5)); ax.text(x + 2, y + 2, h["inst"], fontsize=5)
        for k, b in lc["bands"].items():
            for r in [b["rect_um"]] + b.get("rects_um", []):
                m = k.startswith("monitor")
                ax.add_patch(Rectangle((r[0], r[1]), r[2] - r[0], r[3] - r[1], fc="red" if m else "#f5c26b",
                                       ec="red" if m else "#a70", alpha=.8 if m else .4, lw=1.5 if m else .3))
                if m:
                    ax.text(r[2] + 3, r[1], f"{k} hop {b.get('max_pin_to_band_hop_um')}", fontsize=7, color="red")
        for p in lc["pins"]:
            if p["name"].startswith(("cland_dn_ready_", "cland_dn_fault_", "fclk_in_cland_dn_")):
                ax.plot(*p["xy_um"], "b^", ms=5)
        if ck.get("tap_mode") == "density":
            sys.path.insert(0, "tools/die_plan")
        ax.set_xlim(-10, W + 120); ax.set_ylim(-10, H + 10); ax.set_aspect("equal")
        ax.set_title(f"{tn} {lab}\ntap_target {ck.get('tap_target_sinks')}", fontsize=8)
    fig.savefig(f"{OUT}/bands_{tn}.png", dpi=110, bbox_inches="tight"); plt.close(fig)
    print(tn)
