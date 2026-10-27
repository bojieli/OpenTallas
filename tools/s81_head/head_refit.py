#!/usr/bin/env python3
"""HEAD-CORE-LAT-R5 predictor refit for HEAD: per-leaf meas = a + b*pred (TT rise, FF early), fit on calibration A, validate on B.
usage: head_refit.py CAL_A.json CAL_B.json OUT.json     (inputs = head_cal_compare.py outputs). Scope: 2 builds, UNCHECKED."""
import json, sys, statistics as st
A, B, out = sys.argv[1:4]
def rows(p, c):
    L = json.load(open(p))["leaves"]
    return [(v["pred_" + c], v["meas_" + c]) for v in L.values() if v.get("meas_" + c) is not None]
def fit(r):
    xs, ys = zip(*r); mx, my = st.mean(xs), st.mean(ys)
    b = sum((x - mx) * (y - my) for x, y in r) / sum((x - mx) ** 2 for x in xs); return my - b * mx, b
def stats(r, a=0.0, b=1.0):
    pr = [a + b * x for x, _ in r]; ms = [y for _, y in r]; res = [m - p for m, p in zip(ms, pr)]
    return dict(pred_mean=round(st.mean(pr), 2), pred_window=round(max(pr) - min(pr), 2), meas_mean=round(st.mean(ms), 2),
                meas_window=round(max(ms) - min(ms), 2), resid_mean=round(st.mean(res), 2), resid_sd=round(st.pstdev(res), 2),
                resid_min=round(min(res), 2), resid_max=round(max(res), 2), r=round(st.correlation([x for x, _ in r], ms), 3))
o = dict(argv=sys.argv, scope="per-leaf linear refit, fit=A validate=B, UNCHECKED")
for c in ("TT_rise", "FF_early"):
    ra, rb = rows(A, c), rows(B, c); a, b = fit(ra)
    o[c] = dict(fit=dict(a=round(a, 3), b=round(b, 4)), A_raw=stats(ra), A_fit=stats(ra, a, b), B_raw=stats(rb), B_fit=stats(rb, a, b))
    print(c, "a %.2f b %.3f" % (a, b), "| B raw", o[c]["B_raw"], "| B fit", o[c]["B_fit"])
json.dump(o, open(out, "w"), indent=1)
