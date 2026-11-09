#!/usr/bin/env python3
"""render one svc type of a split plan (DIE-S81-85 11-09): python3 render_svc_split_1109.py PLAN TYPE OUT.png TITLE"""
import json
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

plan, tn, out, title = sys.argv[1:5]
P = json.load(open(plan))
t = P["partition_types"][tn]
W, H = t["outline_um"]
COL = {"ot_s81c_attn_hcore": "#4C8BC4", "dsdv_svc_sx_hrow": "#B48CC0", "ot_s81_su_sml_fold2": "#F2B35E",
       "ot_s81_svc_merge_h4": "#E8888A", "ot_s81_su_smd_fold2": "#EED36A", "ot_hdc_v41x_idx_hslice_fp": "#A9C4E8"}
fig, ax = plt.subplots(figsize=(7.2, 7.2 * H / W * 0.62 + 1.2))
ax.add_patch(Rectangle((0, 0), W, H, fill=False, lw=1.6, ec="black"))
for c in t["contents"]:
    if "origin_um" in c and "outline_um" in c:
        ax.add_patch(Rectangle(c["origin_um"], *c["outline_um"], fc="#7FB48C", ec="#2E5E3A", lw=0.3))
for h in t["hard_cores"]:
    m = h["module"]
    glue = m.startswith("dsdv_svc_glue")
    fc = "#BDBDBD" if glue else COL.get(m, "#999999")
    ax.add_patch(Rectangle(h["origin_um"], *h["outline_um"], fc=fc, ec="black", lw=0.4, ls="--" if glue else "-"))
    x, y = h["origin_um"]
    w, hh = h["outline_um"]
    lab = None
    if glue:
        lab = m.split("_glue_")[1].split("_", 1)[1].upper() + f"\n{h['cells'] // 1000}k"
    elif m == "ot_s81c_attn_hcore":
        lab = "RT2 " + h["inst"].split("g_t[")[1][0] + "." + h["inst"].split("g_h[")[1].split("]")[0]
    elif m in ("ot_s81_su_sml_fold2",):
        lab = "SML" + h["inst"].split("g_l[")[1][0]
    elif m == "ot_s81_su_smd_fold2":
        lab = "SMD" + h["inst"].split("g_p[")[1][0]
    elif m == "ot_s81_svc_merge_h4":
        lab = "H4\n" + h["inst"].split("g_m[")[1][0] + "." + h["inst"].split("g_h4[")[1][0]
    elif m == "ot_hdc_v41x_idx_hslice_fp":
        lab = "I" + h["inst"].split("g_ch[")[1][0] + h["inst"].split("g_s[")[1][0]
    if lab:
        ax.text(x + w / 2, y + hh / 2, lab, ha="center", va="center", fontsize=4.2)
bay = t["clock"]["tap_um"]
ax.plot(*bay, marker="o", mfc="none", mec="red", ms=7)
ax.set_xlim(-30, W + 30)
ax.set_ylim(-30, H + 30)
ax.set_aspect("equal")
ax.set_title(f"{title}\n{tn}  outline {W} x {H} um", fontsize=8)
ax.tick_params(labelsize=6)
fig.tight_layout()
fig.savefig(out, dpi=170)
