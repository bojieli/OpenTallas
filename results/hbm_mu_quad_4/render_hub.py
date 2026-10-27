#!/usr/bin/env python3
"""render_hub.py PLAN_BEFORE PLAN_AFTER OUT.png --tools B1N: q_hub_nw / q_hub_ne hard cores before/after the
HBM-MU-QUAD-4 re-pin.  Pins drawn in the type frame after orient (sampled), green = the pin's face looks at a partner
of its port (best cos >= 0), red = faces away; grey cores = no plan connectivity.  Title gives away/total port groups."""
import json, sys, re, math, collections
from pathlib import Path
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
sys.path.insert(0, str(Path(__file__).resolve().parent))
import type_reduce as TR

a = sys.argv[1:]
tools = a[a.index("--tools") + 1]
sys.path.insert(0, tools)
import schema as S, check as C
plans = [Path(a[0]), Path(a[1])]
fig, ax = plt.subplots(2, 2, figsize=(20, 12))
for col, pd in enumerate(plans):
    raw = json.loads((pd / "die_plan.json").read_text())
    D = TR.partner_dirs(C, S, pd, raw)
    for row, tn in enumerate(("q_hub_nw", "q_hub_ne")):
        t = raw["partition_types"][tn]; A = ax[row][col]
        W, H = t["outline_um"]
        A.add_patch(Rectangle((0, 0), W, H, fill=False, ec="k", lw=1))
        bad = tot = 0
        for hc in t["hard_cores"]:
            x0, y0 = hc["origin_um"]; w, h = hc["outline_um"]; o = hc.get("orient", "R0")
            d = D.get((tn, hc["inst"]), {})
            A.add_patch(Rectangle((x0, y0), w, h, fc="0.85" if not d else "0.95", ec="k", lw=0.4))
            if not hc.get("pins_file"):
                A.add_patch(Rectangle((x0, y0), w, h, fc="none", ec="m", lw=1.5, hatch="//"))
                continue
            pins = TR.load_pins(pd, hc["pins_file"])
            grp = collections.defaultdict(list)
            for p in pins:
                grp[TR.base(p["name"])].append(p)
            for b, ps in grp.items():
                if b not in d:
                    continue
                for i, p in enumerate(ps):
                    f = TR.tface(o, TR.lface(p["x"], p["y"], w, h))
                    ok = TR.score(d[b], f) >= 0
                    tot += 1; bad += not ok
                    if i % 8:
                        continue
                    px = p["x"] if o in ("R0", "MX") else w - p["x"]
                    py = p["y"] if o in ("R0", "MY") else h - p["y"]
                    A.plot(x0 + px, y0 + py, ".", ms=1.5, color="g" if ok else "r")
        A.set_xlim(0, W); A.set_ylim(0, H); A.set_aspect("equal")
        A.set_title(f"{tn} {'before (planU3f)' if col == 0 else 'after (planU4b)'}: {bad}/{tot} pins face away", fontsize=10)
plt.tight_layout(); plt.savefig(a[2], dpi=100)
print("wrote", a[2])
