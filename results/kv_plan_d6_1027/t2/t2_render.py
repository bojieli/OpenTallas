import json, sys
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
out = sys.argv[1]
r = json.load(open(f"{out}/t2_apply_report.json")); pv = json.load(open(f"{out}/pv_pair_slice_split.json"))
fig, axs = plt.subplots(1, 3, figsize=(21, 6.5), gridspec_kw=dict(width_ratios=[1, 1, 2]))
srams = [(15.552, 13.26, 94.824, 41.064), (15.552, 127.404, 94.824, 41.064)]
for ax, m in zip(axs[:2], ["qkd_ectlk_q0", "qkd_ectlk_q2"]):
    e = r["ectlk"][m]; J = json.load(open(f"{out}/{e['pins_file_new']}"))
    ax.add_patch(Rectangle((0, 0), 216, 172.8, fill=False, ls="--", ec="grey", lw=1, label="old 216x172.8"))
    ax.add_patch(Rectangle((0, 0), 155.52, 172.8, fill=False, ec="k", lw=2, label="new 155.52x172.8 (SW anchor)"))
    for i, (x, y, w, h) in enumerate(srams):
        ax.add_patch(Rectangle((x, y), w, h, fc="#9ecae1", ec="b", label="SRAM 128x256 (kit q0)" if i == 0 else None))
    ax.add_patch(Rectangle((0, 0), 11.232, 172.8, fc="#fdd0a2", alpha=.5, label="W channel 11.232"))
    for i, rr in enumerate(e["core_islands_kept"]):
        ax.add_patch(Rectangle((rr[0], rr[1]), rr[2] - rr[0], max(rr[3] - rr[1], 1.5), fc="r", label="12.2a1 in-core island" if i == 0 else None))
    ei = e["entry_island_um"]
    ax.add_patch(Rectangle((ei[0], ei[1]), 8.64, 8.64, fc="g", alpha=.6, label="12.8a entry island"))
    col = dict(M4="m", M5="c")
    for L in ("M4", "M5"):
        P = [p for p in J["pins"] if p["layer"] == L]
        ax.scatter([p["x"] for p in P], [p["y"] for p in P], s=2, c=col[L], label=f"{L} pins")
    ax.set_xlim(-8, 224); ax.set_ylim(-8, 181); ax.set_aspect("equal")
    ax.set_title(f"{m}: faces {e['faces']}\nentry {e['entry_xy_um']}  far {e['single_tree']['far_new_um']}")
    ax.legend(fontsize=6, loc="upper right")
ax = axs[2]
w, h = pv["outline_um"]
ax.add_patch(Rectangle((0, 0), w, h, fill=False, ec="k", lw=2))
ex, ey = pv["entry"]["xy_um"]; ei = pv["entry"]["island_um"]
ax.add_patch(Rectangle((ei[0], ei[1]), 8.64, 8.64, fc="g", alpha=.6, label="entry island"))
for k, q in enumerate(pv["core_tree"]["islands"]):
    rr = q["rect_um"]; cx, cy = q["centre_um"]
    ax.add_patch(Rectangle((rr[0], rr[1]), 8.64, 8.64, fc="orange", label="12.8b leaf islands" if k == 0 else None))
    ax.plot([ex, cx], [ey, cy], "orange", lw=2)
    x0 = 0 if cx < ex else ex
    ax.add_patch(Rectangle((x0, 0), w / 2, h, fill=False, ls=":", ec="orange"))
for k, rr in enumerate(pv["die_core_islands_12_2a1"]):
    ax.add_patch(Rectangle((rr[0], rr[1]), rr[2] - rr[0], 2, fc="r", label="12.2a1 die islands" if k == 0 else None))
ax.set_xlim(-8, w + 8); ax.set_ylim(-8, h + 8); ax.set_aspect("equal")
ct = pv["core_tree"]
ax.set_title(f"kv3_pv_pair W/E split: grid {ct['grid']} leaf reach {ct['leaf_reach_um']} (<=220)\npred TT {ct['pred_TT_ps']} FF {ct['pred_FF_ps']} (MODEL UNCHECKED); single far {pv['replaces']['far_um']}")
ax.legend(fontsize=7, loc="upper right")
plt.tight_layout(); plt.savefig(f"{out}/t2_geom.png", dpi=110)
