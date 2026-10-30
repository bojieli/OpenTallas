#!/usr/bin/env python3
"""DIE-KV-47-SD render: kv3_sys_SD/_v1 type frame, old (plan of record) vs new reset/collector sites, bands, macro.
usage: render_sd47.py OLD_PLAN NEW_PLAN OUT_PREFIX"""
import json, sys
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
old, new, pre = sys.argv[1:4]
O, N = json.load(open(old)), json.load(open(new))
for tn in ("kv3_sys_SD", "kv3_sys_SD_v1"):
    fig, axs = plt.subplots(2, 1, figsize=(16, 18))
    for ax, P, lab in ((axs[0], O, "OLD plan of record event28w_c"), (axs[1], N, "NEW DIE-KV-47-SD re-site")):
        t = P["partition_types"][tn]; w, h = t["outline_um"]; lc = t["clock"]["landing_contract"]; T = lc["collector_tree"]
        ax.add_patch(Rectangle((0, 0), w, h, fill=False, ec="k", lw=1.5))
        ax.add_patch(Rectangle((17.28, 54), 1848.96, 972, fc="#ddd", ec="#888", lw=1, label="x6 PHY macro footprint"))
        for k, b in lc["bands"].items():
            x0, y0, x1, y1 = b["rect_um"]
            ax.add_patch(Rectangle((x0, y0), x1-x0, y1-y0, fc="#6c6", ec="g", alpha=.7))
            ax.text(x1, y1 + 4, k, fontsize=7, color="g", ha="right")
        xy = {r["q"]: r["xy"] for r in T["relays"]}; xy[lc["collector_root_node"]] = T["root"]
        for r in T["relays"]:
            if r["d"] in xy:
                a, b = xy[r["d"]], r["xy"]
                ax.plot([a[0], b[0], b[0]], [a[1], a[1], b[1]], "-", color="#88f", lw=.6)
        ax.scatter([r["xy"][0] for r in T["relays"]], [r["xy"][1] for r in T["relays"]], s=14, c="b", label=f"collector/reset relays ({len(T['relays'])})", zorder=3)
        lt = t["reset"]["local_taps_um"]
        ax.scatter([p[0] for p in lt], [p[1] for p in lt], s=60, marker="x", c="r", label=f"reset.local_taps_um ({len(lt)})", zorder=4)
        ax.scatter([T["root"][0]], [T["root"][1]], s=80, marker="*", c="m", label="tree root (arst_n)", zorder=5)
        for p in lc["pins"]:
            ax.plot(*p["xy_um"], "k^", ms=4)
        for s_ in lc["collector_local_sources"]:
            q = xy.get(f"rst_n_t{s_['tap']}")
            if q: ax.plot([s_["xy_um"][0], q[0]], [s_["xy_um"][1], q[1]], "m--", lw=1)
        ax.set_xlim(-20, w + 20); ax.set_ylim(-20, h + 20); ax.set_aspect("equal")
        ax.set_title(f"{tn}  {lab}: depth {T['depth']} max hop {T['max_hop_um']}"); ax.legend(loc="center", fontsize=8)
    fig.tight_layout(); fig.savefig(f"{pre}_{tn}.png", dpi=80)
    # zoom: E strip + S-E corner
    fig, ax = plt.subplots(1, 2, figsize=(16, 9))
    for a_, P, lab in ((ax[0], O, "OLD"), (ax[1], N, "NEW")):
        t = P["partition_types"][tn]; lc = t["clock"]["landing_contract"]; T = lc["collector_tree"]
        a_.add_patch(Rectangle((17.28, 54), 1848.96, 972, fc="#ddd", ec="#888"))
        a_.add_patch(Rectangle((0, 0), 1900.8, 1036.8, fill=False, ec="k"))
        for k, b in lc["bands"].items():
            x0, y0, x1, y1 = b["rect_um"]; a_.add_patch(Rectangle((x0, y0), x1-x0, y1-y0, fc="#6c6", ec="g", alpha=.7))
        a_.scatter([r["xy"][0] for r in T["relays"]], [r["xy"][1] for r in T["relays"]], s=18, c="b", zorder=3)
        lt = t["reset"]["local_taps_um"]; a_.scatter([p[0] for p in lt], [p[1] for p in lt], s=60, marker="x", c="r", zorder=4)
        for p in lc["pins"]: a_.plot(*p["xy_um"], "k^", ms=5)
        a_.set_xlim(1650, 1905); a_.set_ylim(-5, 1040); a_.set_title(f"{tn} {lab} E strip zoom (x 1650-1905)")
    fig.tight_layout(); fig.savefig(f"{pre}_{tn}_Ezoom.png", dpi=80)
print("ok")
