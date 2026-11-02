#!/usr/bin/env python3
"""HBM-CORES-KITS-41/COMPACT render: left = new core frame (outline, macros + 4.32 halo, clock island, pins by layer);
right = parent context: every instance of the module in one hub type, old outline (dashed) vs new (solid), neighbouring hard cores.
usage: k41_render.py PLANDIR MODULE PTYPE OUT.png"""
import json, sys, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
D, MOD, PT, OUT = sys.argv[1:5]
plan = json.load(open(D + "/die_plan.json")); cm = json.load(open(D + "/core_macros.json"))["cores"][MOD]
ce = json.load(open(D + "/clock_entries.json")); rep = json.load(open(D + "/k41_event_report.json"))
v = plan["partition_types"][PT]; hcs = [h for h in v["hard_cores"] if h["module"] == MOD]
fig, (a, b) = plt.subplots(1, 2, figsize=(20, 10))
W, H = cm["outline_um"]; a.add_patch(Rectangle((0, 0), W, H, fill=False, lw=1.5))
for m in cm["macros"]:
    x0, y0, x1, y1 = m["rect_um"]
    a.add_patch(Rectangle((x0 - 4.32, y0 - 4.32), x1 - x0 + 8.64, y1 - y0 + 8.64, fc="#fde2b0", ec="none"))
    a.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fc="#d08a2c", ec="k", lw=.5)); a.text((x0 + x1) / 2, (y0 + y1) / 2, m["name"].split(".")[-2] + "." + m["name"].split(".")[-1] + " " + m["orient"], ha="center", fontsize=7)
e = ce[PT][hcs[0]["inst"]]; ix0, iy0, ix1, iy1 = e["island_um"]
a.add_patch(Rectangle((ix0, iy0), ix1 - ix0, iy1 - iy0, fc="#9ad0f5", ec="b")); a.plot(*e["xy_um"], "b+", ms=12)
pins = json.load(open(D + "/" + hcs[0]["pins_file"]))
col = {"M4": "g", "M5": "r", "M6": "m", "M7": "c"}
for L in col:
    p = [q for q in pins if q["layer"] == L and "clk" not in q["name"]]
    if p: a.scatter([q["x"] for q in p], [q["y"] for q in p], s=1, c=col[L], label="%s %d" % (L, len(p)))
ck = [q for q in pins if "clk" in q["name"]]; a.scatter([q["x"] for q in ck], [q["y"] for q in ck], s=14, c="b", marker="s", label="clk pins %d" % len(ck))
a.set_aspect("equal"); a.set_xlim(-5, W + 5); a.set_ylim(-5, H + 5); a.legend(loc="upper right", fontsize=8)
a.set_title("%s NEW %.2fx%.2f, inst0 %s pins %s (%d)" % (MOD, W, H, hcs[0]["inst"], hcs[0]["pins_file"].split("/")[-1][-30:], len(pins)), fontsize=9)
old = {c["inst"]: c for c in rep["changed_instances"] if c["type"] == PT}
xs, ys = [], []
for h in v["hard_cores"]:
    ox, oy = h["origin_um"]; w, hh = h["outline_um"]
    if h["module"] == MOD:
        c = old[h["inst"]]; o = c["old_origin"]; ow, oh = c["old_outline"]
        b.add_patch(Rectangle(o, ow, oh, fill=False, ls="--", ec="gray"))
        b.add_patch(Rectangle((ox, oy), w, hh, fc="#7fc97f", ec="g", alpha=.8)); b.text(ox + w / 2, oy + hh / 2, h["inst"] + "\n" + h.get("orient", "R0"), ha="center", fontsize=6)
        xs += [o[0], o[0] + ow]; ys += [o[1], o[1] + oh]
for h in v["hard_cores"]:
    if h["module"] == MOD: continue
    ox, oy = h["origin_um"]; w, hh = h["outline_um"]
    if min(xs) - 300 < ox + w and ox < max(xs) + 300 and min(ys) - 300 < oy + hh and oy < max(ys) + 300:
        b.add_patch(Rectangle((ox, oy), w, hh, fc="#cccccc", ec="k", lw=.3, alpha=.6))
for t in v["clock"]["taps"]:
    if t["name"] in old: b.plot(*t["xy"], "b+", ms=6)
b.set_xlim(min(xs) - 300, max(xs) + 300); b.set_ylim(min(ys) - 300, max(ys) + 300); b.set_aspect("equal")
b.set_title("%s: %d instances of %s; dashed = old slot, green = new outline, + = clock tap; grey = other hard cores" % (PT, len(hcs), MOD), fontsize=9)
plt.tight_layout(); plt.savefig(OUT, dpi=110); print(OUT)
