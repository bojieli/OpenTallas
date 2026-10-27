#!/usr/bin/env python3
"""HEAD-CORE-LAT-R6: apply the HEAD per-leaf refit (meas = a + b*pred; R5 cal1/cal2, both fit directions) to a
uf_phys pred.json -> refit mean/window TT rise + FF early. HEAD refit, NOT MODEL-REFIT-3. UNCHECKED.
usage: head_refit_apply.py PRED.json REFIT_A1_B2.json REFIT_A2_B1.json [OUT.json]"""
import json, sys, statistics as st
P = json.load(open(sys.argv[1])); fits = [json.load(open(f)) for f in sys.argv[2:4]]
o = dict(argv=sys.argv, model="HEAD per-leaf refit R5 (2 builds, one geometry), band means +-5 TT / +-3 FF, windows +-5",
         note="NOT MODEL-REFIT-3; UNCHECKED")
for c, leafk, sub in (("TT_rise", "TT_leaf", "rise"), ("FF_early", "FF_leaf", "early")):
    xs = [v[sub] for v in P[leafk].values()]
    o[c] = dict(raw=dict(mean=round(st.mean(xs), 2), window=round(max(xs) - min(xs), 2)))
    for i, F in enumerate(fits):
        a, b = F[c]["fit"]["a"], F[c]["fit"]["b"]
        ys = [a + b * x for x in xs]
        o[c]["fit%d" % (i + 1)] = dict(a=a, b=b, mean=round(st.mean(ys), 2), window=round(max(ys) - min(ys), 2))
    o[c]["worst_window"] = max(o[c]["fit1"]["window"], o[c]["fit2"]["window"])
print(json.dumps({k: o[k] for k in ("TT_rise", "FF_early")}))
if len(sys.argv) > 4:
    json.dump(o, open(sys.argv[4], "w"), indent=1)
