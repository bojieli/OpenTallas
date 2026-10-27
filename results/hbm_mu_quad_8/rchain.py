#!/usr/bin/env python3
"""QUAD-8 render: c14 vs c15 station chains that changed (per type), cores grey, c14 chain red dashed, c15 chain blue, +1 chains green.
Also xq pin faces before/after.  usage: rchain.py C14 C15 OUTDIR"""
import json, sys, matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt, matplotlib.patches as mp
from pathlib import Path
a, b, o = map(Path, sys.argv[1:4]); o.mkdir(exist_ok=True)
pa = json.loads((a/"die_plan.json").read_text()); pb = json.loads((b/"die_plan.json").read_text())
rp = json.loads((b/"relax_route_report.json").read_text()); added = {(x["type"], x["conn"]) for x in rp["added_one_reg"]}
for tn, tb in pb["partition_types"].items():
    ta = pa["partition_types"][tn]
    ch = [(e0, e) for e0, e in zip(ta.get("internal_stations") or [], tb.get("internal_stations") or []) if e["regs_um"] != e0["regs_um"]]
    if not ch: continue
    W, H = tb["outline_um"]; f, ax = plt.subplots(figsize=(14, 14*H/W if W > H else 14))
    for h in tb.get("hard_cores") or []:
        x, y = h["origin_um"]; w, hh = h["outline_um"]; ax.add_patch(mp.Rectangle((x, y), w, hh, fc="0.8", ec="0.4", lw=.4))
    for e0, e in ch:
        P0 = [e0["from_um"]]+e0["regs_um"]+[e0["to_um"]]; P1 = [e["from_um"]]+e["regs_um"]+[e["to_um"]]
        ax.plot(*zip(*P0), "r--", lw=.5, alpha=.6); ax.plot(*zip(*e0["regs_um"]), "rx", ms=3) if e0["regs_um"] else None
        c = "g" if (tn, e["conn"]) in added else "b"
        ax.plot(*zip(*P1), c+"-", lw=.8); ax.plot(*zip(*e["regs_um"]), c+"o", ms=2.5)
    ax.set_xlim(0, W); ax.set_ylim(0, H); ax.set_aspect("equal")
    ax.set_title(f"{tn}: {len(ch)} chains re-placed (red x/dash = c14, blue = c15 count kept, green = c15 +1)", fontsize=9)
    f.savefig(o/f"chains_{tn}.png", dpi=110, bbox_inches="tight"); plt.close(f); print(tn, len(ch))
# xq pins
import glob
for tag, d in (("c14", a), ("c15", b)):
    pins = json.loads((d/"cores/ot_hgi_sm_xload_xq_pegress__181.44x276.48__content_trial.json").read_text())
    f, ax = plt.subplots(figsize=(6, 8)); ax.add_patch(mp.Rectangle((0, 0), 181.44, 276.48, fc="0.9", ec="k"))
    for L, c in (("M4", "b"), ("M5", "m"), ("M3", "c")):
        q = [p for p in pins if p.get("layer") == L]; ax.plot([p["x"] for p in q], [p["y"] for p in q], c+".", ms=1, label=f"{L} {len(q)}")
    ck = [p for p in pins if p["name"].startswith("clk")]; ax.plot([p["x"] for p in ck], [p["y"] for p in ck], "r*", ms=8, label="clk*")
    ax.set_xlim(-10, 192); ax.set_ylim(-10, 287); ax.set_aspect("equal"); ax.legend(fontsize=7, loc="center"); ax.set_title(f"xq_pegress pins {tag}")
    f.savefig(o/f"xq_pins_{tag}.png", dpi=110, bbox_inches="tight"); plt.close(f)
