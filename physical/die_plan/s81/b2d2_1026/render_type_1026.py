#!/usr/bin/env python3
"""PATH-S81-R3: render one partition type of a die plan (hard cores + orient, core pins by port, bus windows,
12.8 clock entries + parent tap, internal-station regs).  usage: render_type_1026.py REPO PLAN TYPE OUT.png"""
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

REPO, PLAN, TN, OUT = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3], sys.argv[4]
sys.path[:0] = [str(REPO / "tools" / "die_plan")]
import check as C  # noqa: E402

raw = json.loads(PLAN.read_text())
t = raw["partition_types"][TN]
W, H = t["outline_um"]
fig, ax = plt.subplots(figsize=(18, 18 * H / W + 1.5))
ax.add_patch(Rectangle((0, 0), W, H, fill=False, lw=2, ec="k"))
cmap = plt.get_cmap("tab20")
ports = {}
for hc in t.get("hard_cores", []):
    (ox, oy), (cw, ch) = hc["origin_um"], hc["outline_um"]
    o = hc.get("orient", "R0")
    ax.add_patch(Rectangle((ox, oy), cw, ch, fc="#dde6f0", ec="#335", lw=1.2))
    ax.text(ox + cw / 2, oy + ch / 2 + ch * 0.18, f"{hc['inst'].split('.')[-1] if 'g_q' not in hc['inst'] else hc['inst'].split('.')[-2]}\n"
            f"{hc['module']} {o}\n{cw:g}x{ch:g}", ha="center", va="center", fontsize=8)
    pins = C.core_pins(hc, PLAN.parent)
    by = {}
    for n, ln, x, y in pins:
        by.setdefault(n.split("[")[0], []).append(C._orient_pt(o, cw, ch, x, y))
    for p, pts in by.items():
        c = ports.setdefault(p, cmap(len(ports) % 20))
        xs = [ox + a for a, _ in pts]
        ys = [oy + b for _, b in pts]
        ax.scatter(xs, ys, s=1.5, color=c, label=p if p not in ax.get_legend_handles_labels()[1] else None)
for b in t.get("buses", []):
    lo, hi = b["window_um"]
    f = b["face"]
    seg = {"S": ([lo, hi], [0, 0]), "N": ([lo, hi], [H, H]), "W": ([0, 0], [lo, hi]), "E": ([W, W], [lo, hi])}[f]
    ax.plot(*seg, lw=6, color="#c33" if b["dir"] == "out" else "#393", solid_capstyle="butt")
    tx, ty = (sum(seg[0]) / 2, sum(seg[1]) / 2)
    ax.text(tx, ty + (-25 if f == "S" else 25 if f == "N" else 0), b["name"], fontsize=7, ha="center",
            rotation=90 if f in "WE" else 0)
ck = t.get("clock", {}) or {}
if ck.get("tap_um"):
    ax.plot(*ck["tap_um"], marker="*", ms=22, color="gold", mec="k", label="parent clock tap")
for tp in ck.get("taps", []):
    if tp.get("kind") == "core":
        ax.plot(*tp["xy"], marker="P", ms=12, color="m", mec="k")
        ax.text(tp["xy"][0] + 10, tp["xy"][1] - 18, f"{tp.get('insertion_ps')}", fontsize=7, color="m")
for st in t.get("internal_stations", []) or []:
    for r in st.get("regs_um", []):
        ax.plot(*r, marker="s", ms=6, color="orange", mec="k")
for s in t.get("ft_slots", []) or []:
    for r in s.get("regs_um", []):
        ax.plot(*r, marker="o", ms=4, color="c", mec="k")
ax.set_xlim(-60, W + 60)
ax.set_ylim(-60, H + 60)
ax.set_aspect("equal")
ax.legend(loc="upper left", bbox_to_anchor=(1.0, 1.0), fontsize=7, markerscale=6)
ax.set_title(f"{TN}  {W:g}x{H:g} um  ({PLAN.name})  magenta P = 12.8 centre clock entry (TT ps), gold * = parent tap")
fig.tight_layout()
fig.savefig(OUT, dpi=110)
print(OUT)
