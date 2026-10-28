#!/usr/bin/env python3
"""DIE-S81-8: declared-budget FF intra hold (die_sta_related zero-logic model, main tool imported) binned by the
Manhattan distance between the two clock taps' xy.  The declared model times EVERY ordered tap pair of a partition as a
direct flop->flop path at clk->Q min with no wire; a pair whose taps are far apart cannot have a zero-wire path (reach
405 um/hop), so the far bins show how much of -162.5 is the all-pairs artefact.  usage: hold_dist.py TOOLS PROOF PLAN REG_FF.json OUT"""
import json, sys
from pathlib import Path
from collections import defaultdict
tools, proof, plan_p, reg_p, out_p = sys.argv[1:6]
sys.path.insert(0, tools)
import die_sta_related as D  # noqa: E402
D.CPPR_LCA = True
plan = json.loads(Path(plan_p).read_text())
reg = json.loads(Path(reg_p).read_text())
res = {}
for c in ("FF",):
    meta, taps = D.load_taps(Path(proof), c)
    meta, taps = D.scale_clock(meta, taps, D.SPICE_CLOCK_CAL[c])
    rng = meta["cppr_node_range_ps"]
    pairs, _ = D.build_pairs(plan, taps)
    dreg = D.droop_regions(Path(proof), taps, "mesh", str(Path(proof) / "droop_regions.json"))
    ocv = D.clock_ocv_fn("table", "shared", dict(meta, corner=c), taps, 202.5, region=dreg)
    base = reg["clkq_min_nowire_ps"] - reg["hold_ps"] - D.UNC_HOLD_PS
    edges = [0, 100, 200, 400, 800, 1600, 3200, 1e9]
    B = defaultdict(lambda: dict(n=0, neg=0, worst=1e9, w=None, dmg=0.0, ocv=0.0))
    for a, b, tag in pairs["intra"]:
        TA, TB = taps[a], taps[b]
        dist = abs(TA["xy_um"][0] - TB["xy_um"][0]) + abs(TA["xy_um"][1] - TB["xy_um"][1])
        k = next(i for i in range(len(edges) - 1) if dist < edges[i + 1])
        node = D.pair_node(TA, TB)
        la, ea, lc, ec = D.arr4(TA, TB, node)
        cr = D.credit(rng, node, la, ea, lc, ec)
        dmg, oh = lc - ea - cr, ocv(a, b, "hold")
        h = base - dmg - oh
        x = B[f"{edges[k]:g}-{edges[k+1]:g}"]
        x["n"] += 1
        x["neg"] += h < 0
        if h < x["worst"]:
            x.update(worst=round(h, 1), w=[a, b, round(dist, 1)], dmg=round(dmg, 1), ocv=round(oh, 1))
    res[c] = dict(base_ps=round(base, 2), bins=dict(B))
    for k, v in B.items():
        print(c, k, v)
Path(out_p).write_text(json.dumps(res, indent=1))
