#!/usr/bin/env python3
"""S81-P9-PLAN49 v4.9: render one partition type of a die_plan.json: outline, hard cores, internal_stations (FIRM plan
stations, polylines from -> regs -> to), ft slot station sites (regs_um) and the leaf bundle hops (hard_core_gaps.json).
usage: render_type_v49.py PLAN_DIR TYPE OUT.png"""
import json, sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle


def main(pd, tn, out):
    P = json.load(open(pd + "/die_plan.json"))
    t = P["partition_types"][tn]
    W, H = t["outline_um"]
    fig, ax = plt.subplots(figsize=(10, 10 * H / W if H / W < 2 else 16))
    ax.add_patch(Rectangle((0, 0), W, H, fill=False, lw=1.5))
    for c in t.get("hard_cores", []):
        (x, y), (w, h) = c["origin_um"], c["outline_um"]
        dx, dy = c.get("track_offset_um", [0, 0])
        ax.add_patch(Rectangle((x + dx, y + dy), w, h, fc="#dde6f0", ec="k", lw=0.6))
        lab = c["inst"].split(".")[-1] if "hc.g_h" not in c["inst"] else c["inst"].split("g_t[")[1][0] + "/" + \
            c["inst"].split("g_h[")[1].split("]")[0]
        ax.text(x + dx + w / 2, y + dy + h / 2, "%s\n%gx%g" % (lab, w, h), ha="center", va="center", fontsize=6)
    for e in t.get("internal_stations", []):
        pts = [e["from_um"]] + e["regs_um"] + [e["to_um"]]
        ax.plot([p[0] for p in pts], [p[1] for p in pts], "-", color="tab:green", lw=0.5, alpha=0.6)
        ax.scatter([p[0] for p in e["regs_um"]], [p[1] for p in e["regs_um"]], s=10, color="red", zorder=5)
    for s in t.get("ft_slots", []):
        if s.get("regs_um"):
            r = s["regs_um"]
            ax.plot([p[0] for p in r], [p[1] for p in r], ":", color="tab:purple", lw=0.8)
            ax.scatter([p[0] for p in r[1:]], [p[1] for p in r[1:]], s=8, marker="s", color="tab:purple", zorder=5)
    try:
        hops = json.load(open(pd + "/hard_core_gaps.json"))["v49"]["leaf_bundles"].get(tn, [])
    except Exception:
        hops = []
    worst = max([r["worst_hop_um"] for r in hops], default=0)
    nst = sum(len(e["regs_um"]) for e in t.get("internal_stations", []))
    nft = sum(1 for s in t.get("ft_slots", []) if s.get("regs_um"))
    ax.set_xlim(-10, W + 10); ax.set_ylim(-10, H + 10); ax.set_aspect("equal")
    ax.set_title("%s %gx%g (plan v4.9): %d hard cores; red = FIRM internal stations (%d sites, %d links); purple = ft "
                 "corridor sites (%d slots)%s" % (tn, W, H, len(t.get("hard_cores", [])), nst,
                                                  len(t.get("internal_stations", [])), nft,
                                                  "; worst core-core hop %.0f um" % worst if hops else ""), fontsize=7)
    fig.tight_layout(); fig.savefig(out, dpi=110)


if __name__ == "__main__":
    main(*sys.argv[1:4])
