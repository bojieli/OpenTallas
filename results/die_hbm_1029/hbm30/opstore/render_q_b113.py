#!/usr/bin/env python3
"""DIE-HBM-30-O: render q_b113 type frame before (d29d) / after (d30o): hard cores (+ opstore_a/opstore_b macros
from core_macros.json, orient-aware), die_ft_bands, internal station FF homes + chains, clock taps.
usage: render_q_b113.py BEFORE_PLAN_DIR AFTER_PLAN_DIR OUT.png"""
import json, sys
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
def load(d):
    P = json.load(open(d + "/die_plan.json")); CM = json.load(open(d + "/core_macros.json"))["cores"]
    return P["partition_types"]["q_b113"], CM
def xf(h, x, y):
    W, H = h["outline_um"]; o = h.get("orient", "R0"); tx, ty = h.get("track_offset_um", [0, 0])
    if o in ("MY", "R180"): x = W - x
    if o in ("MX", "R180"): y = H - y
    return h["origin_um"][0] + tx + x, h["origin_um"][1] + ty + y
fig, axs = plt.subplots(1, 2, figsize=(20, 9), dpi=110)
for ax, d, title in zip(axs, sys.argv[1:3], ["before d29d", "after d30o"]):
    T, CM = load(d); W, H = T["outline_um"]
    ax.add_patch(Rectangle((0, 0), W, H, fill=False, lw=1.5))
    for b in T["die_ft_bands"]:
        lo, hi = b["span_um"]
        r = (0, lo, W, hi - lo) if b["dir"] == "EW" else (lo, 0, hi - lo, H)
        ax.add_patch(Rectangle(r[:2], r[2], r[3], color="khaki", alpha=0.35))
    for h in T["hard_cores"]:
        x0, y0 = h["origin_um"]; w, hh = h["outline_um"]
        ax.add_patch(Rectangle((x0, y0), w, hh, fill=True, alpha=0.18, ec="navy", lw=1.2))
        ax.text(x0 + w / 2, y0 + hh / 2, h["inst"].replace("u_sfucore_Q_", "") + f"\n{h.get('orient','R0')}", ha="center", va="center", fontsize=9)
        m = CM.get(h["module"], {})
        if m.get("status") == "KNOWN" and m.get("outline_um") == h["outline_um"]:
            for mm in m["macros"]:
                a = xf(h, mm["rect_um"][0], mm["rect_um"][1]); b = xf(h, mm["rect_um"][2], mm["rect_um"][3])
                ax.add_patch(Rectangle((min(a[0], b[0]), min(a[1], b[1])), abs(b[0] - a[0]), abs(b[1] - a[1]), color="grey", alpha=0.6, lw=0))
    for s in T["internal_stations"]:
        pts = [s["from_um"]] + s["regs_um"] + [s["to_um"]]
        ax.plot([p[0] for p in pts], [p[1] for p in pts], "-", lw=0.5, color="green", alpha=0.6)
        ax.plot([p[0] for p in s["regs_um"]], [p[1] for p in s["regs_um"]], "o", ms=3, color="red")
    for t in T["clock"]["taps"]:
        ax.plot(*t["xy"], "x", color="magenta", ms=9, mew=2)
    ax.set_xlim(-20, W + 20); ax.set_ylim(-20, H + 20); ax.set_aspect("equal"); ax.set_title(f"q_b113 {title} (type frame, um); red=station FFs, x=clock taps, khaki=ft bands")
plt.tight_layout(); plt.savefig(sys.argv[3])
