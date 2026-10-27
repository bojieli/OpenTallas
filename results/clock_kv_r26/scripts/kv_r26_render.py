#!/usr/bin/env python3
"""CLOCK-KV-R26 renders: core-frame views (e1/e5 r26 vs e6 r25 entry) + die-frame head groups in 4 partition orients."""
import json, sys
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import schema
from die_clock_mesh import core_frame

pd, out = Path(sys.argv[1]), Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)


def pins(pf):
    return json.loads((pd / pf).read_text())["pins"]


def kind(n):
    s = n.split("__")[-1]
    return "clk" if s.startswith("clk") else "rst" if "rst_n" in s else "strap" if n.startswith("strap") else "data"


COL = dict(clk="red", rst="blue", strap="green", data="0.7")
views = [("e1 r26", "cores/kv3_head_eighth_e1_pins_r26.json"), ("e5 r26", "cores/kv3_head_eighth_e5_pins_r26.json"),
         ("e5 fMX r26 (MX image; unused)", "cores/kv3_head_eighth_e5_pins_fMX_r26.json"), ("e6 r25 (reference)", "cores/kv3_head_eighth_e6_pins_r25.json")]
fig, ax = plt.subplots(2, 4, figsize=(24, 12))
for j, (t, f) in enumerate(views):
    P = pins(f)
    for row, (lim, ms) in enumerate(((((0, 216), (0, 216)), 3), (((105.5, 110.5), (106.8, 109.2)), 40))):
        a = ax[row][j]
        a.add_patch(Rectangle((0, 0), 216, 216, fill=False, ec="k"))
        a.add_patch(Rectangle((108 - 4.32, 108 - 4.32), 8.64, 8.64, fill=True, fc="#ffe9a8", ec="orange", alpha=0.6))
        for k in ("data", "strap", "rst", "clk"):
            xs = [p["x"] for p in P if kind(p["name"]) == k]
            ys = [p["y"] for p in P if kind(p["name"]) == k]
            a.scatter(xs, ys, s=ms if k != "data" else 2, c=COL[k], marker="s" if k == "rst" else "o", label=f"{k} {len(xs)}")
        if row == 1:
            for p in P:
                if kind(p["name"]) in ("clk", "rst") and abs(p["y"] - 108) < 1:
                    a.annotate(p["name"].replace("__", ".").replace("[0]", ""), (p["x"], p["y"]), rotation=90, fontsize=7,
                               xytext=(0, 8 if kind(p["name"]) == "clk" else -60), textcoords="offset points")
            a.set_xlim(*lim[0]); a.set_ylim(*lim[1])
            a.set_title(t + ": centre entry zoom (orange = 8.64 um island)")
        else:
            a.set_xlim(-5, 221); a.set_ylim(-5, 221); a.set_title(t + " core frame 216x216"); a.legend(loc="upper right", fontsize=8)
        a.set_aspect("equal")
fig.tight_layout()
fig.savefig(out / "core_e1_e5_r26.png", dpi=80)

# die frame: one kv3_hg-family partition per partition orient, all 16 head cores, clock+reset pins + taps
P6 = schema.Plan(schema.load(pd / "hm_r26.json"))
raw = P6.raw
seen = {}
for pn, part in P6.parts.items():
    t = P6.ptype(pn)
    if any(h["module"] == "kv3_head_eighth_e5" for h in t.get("hard_cores") or []):
        seen.setdefault(part.get("orient", "R0"), pn)
fig, ax = plt.subplots(1, len(seen), figsize=(7 * len(seen), 9))
for a, (o, pn) in zip(ax, sorted(seen.items())):
    t = P6.ptype(pn)
    for h in t["hard_cores"]:
        if not h["module"].startswith("kv3_head_eighth"):
            continue
        c = [core_frame(P6, pn, h, q, inverse=True) for q in ((0, 0), (216, 216))]
        x0, x1 = sorted([c[0][0], c[1][0]]); y0, y1 = sorted([c[0][1], c[1][1]])
        a.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fill=False, ec="k"))
        cx, cy = core_frame(P6, pn, h, (108, 108), inverse=True)
        a.add_patch(Rectangle((cx - 4.32, cy - 4.32), 8.64, 8.64, fc="#ffe9a8", ec="orange"))
        nm = h["module"][-2:]
        a.text(x0 + 4, y0 + 8, f"{h['inst']} {nm} {h['orient']}", fontsize=8,
               color="purple" if nm in ("e1", "e5") else "k")
        for p in pins(h["pins_file"]):
            k = kind(p["name"])
            if k in ("clk", "rst"):
                x, y = core_frame(P6, pn, h, (p["x"], p["y"]), inverse=True)
                a.scatter([x], [y], s=10, c=COL[k], marker="s" if k == "rst" else "o")
    tps = [tp["xy"] for tp in t["clock"]["taps"] if ".g_t_" in tp["name"]]
    die = [P6.to_die(pn, tuple(xy)) for xy in tps]
    a.scatter([d[0] for d in die], [d[1] for d in die], s=120, facecolors="none", edgecolors="m", label=f"type taps on heads {len(die)}")
    a.set_title(f"{pn} (type {P6.parts[pn]['type']}, part orient {o}) die frame")
    a.set_aspect("equal"); a.legend(loc="upper right", fontsize=8)
    a.autoscale()
fig.tight_layout()
fig.savefig(out / "die_heads_r26.png", dpi=70)
print("ok", sorted(seen.items()))
