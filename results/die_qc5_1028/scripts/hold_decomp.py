#!/usr/bin/env python3
"""DIE-QC-5: FF intra hold = (clkq_min - lib hold - unc_hold) - nominal CPPR'd damage - clock OCV, per region class.
usage: hold_decomp.py TOOLS PKL PROOF"""
import sys, pickle, json, collections, math
sys.path.insert(0, sys.argv[1])
import die_sta_related as R
from pathlib import Path
R.CPPR_LCA = True
S = pickle.load(open(sys.argv[2], "rb"))
meta, taps = R.load_taps(Path(sys.argv[3]), "FF")
rng = meta["cppr_node_range_ps"]
base = 39.746 - 13.799 - 25.0
def cls(p):
    return "c_*" if p.startswith("c_") else ("sl_*_su_c" if p.endswith("su_c") else ("sl_*" if p.startswith("sl_") else "other"))
for nm, call in zip(("intra", "seam"), S["calls"][:2]):
    agg = collections.defaultdict(list)
    for key, v in call["ff"].items():
        a, b, tag = key[:3]
        A, B = taps[a], taps[b]
        node = R.pair_node(A, B)
        la, ea, lc, ec = R.arr4(A, B, node)
        dmg = lc - ea - R.credit(rng, node, la, ea, lc, ec)
        part = tag if nm == "intra" else tag.split("->")[1]
        agg[cls(part)].append((v[1], dmg, base - dmg - v[1]))
    print("==", nm, "(hold = %.2f - damage - ocv)" % base)
    for c, L in sorted(agg.items()):
        L.sort()
        n = len(L); w = L[0]
        def pct(i, q): 
            s = sorted(x[i] for x in L); return s[min(n - 1, int(q * n))]
        print("  %-10s n %6d worst hold %7.1f (dmg %.1f ocv %.1f) | median hold %6.1f dmg %5.1f ocv %5.1f | p99 dmg %5.1f ocv %5.1f | hold<0 with dmg<20: %d"
              % (c, n, w[0], w[1], w[2], pct(0, .5), pct(1, .5), pct(2, .5), pct(1, .99), pct(2, .99), sum(1 for x in L if x[0] < 0 and x[1] < 20)))
