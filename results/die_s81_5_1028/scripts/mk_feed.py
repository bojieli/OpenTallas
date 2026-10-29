#!/usr/bin/env python3
"""DIE-S81-5: region = partition map + locality 'spine' feed (max-bit spanning tree spine through region centres; the
12.14b v3 estimate's 0-FAIL part/spine form) for die_trial --tree-form link_htree.  usage: mk_feed.py WT PLAN V OUTDIR"""
import json, sys
from pathlib import Path
WT, PL, V, O = sys.argv[1], sys.argv[2], float(sys.argv[3]), Path(sys.argv[4])
sys.path.insert(0, WT + "/tools/die_plan")
import locality as LO
D = LO.load_plan(PL)
reg = LO.load_regions("part", D)
FEED = sys.argv[5] if len(sys.argv) > 5 else "spine"
S = LO.score(D, reg, V, FEED)
O.mkdir(parents=True, exist_ok=True)
(O / "map_part.json").write_text(json.dumps(dict(part_region=reg), indent=0, sort_keys=True))
(O / ("feed_part_" + FEED + ".json")).write_text(json.dumps(S["feed"], indent=0))
s = S["summary"]
print(json.dumps({k: s[k] for k in ("regions", "crossing_ports", "off_feed_ports", "max_ins_ps", "max_span_mm",
                                     "feed_root", "feed_joined", "max_tree_hops", "worst_unshared_on_feed_tt",
                                     "worst_unshared_off_feed_tt")}, default=str))
regs = sorted(S["regions"], key=lambda r: -r["ins_ps"])
print("largest region insertion (I = v (w+h)/2):", [(r["region"], r["ins_ps"], r["w_mm"], r["h_mm"]) for r in regs[:8]])
