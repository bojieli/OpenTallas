#!/usr/bin/env python3
"""HEAD-CORE-LAT-R5: measured (meas_ck.tcl, GRT RC rc_cal 0.8,0.9) vs uf_phys predicted per-leaf clock arrival (calibration residual).
usage: cal_compare.py MEAS_TT.tsv MEAS_FF.tsv PRED.json OUT.json
leaf of a sink = its clock net ot_ms_<LEAF>_clk; macro leaves ot_ms_m<k>_clk reported separately.
TT rise = arrival_max_rise; FF early = min(arrival_min_rise, arrival_min_fall); leaf value = mean over the leaf's sinks (= uf_phys leaf basis)."""
import json, re, statistics as st, sys, hashlib
tt, ff, pf, out = sys.argv[1:5]
def rd(p):
    d = {}
    for ln in open(p):
        if ln.startswith("#"): continue
        f = ln.rstrip("\n").split("\t")
        m = re.match(r"ot_ms_(.+)_clk$", f[1])
        if not m: continue
        v = [float(x) if x not in ("nan", "") else float("nan") for x in f[2:6]]
        d.setdefault(m.group(1), []).append(v)
    return d
T, F = rd(tt), rd(ff)
P = json.load(open(pf))
o = dict(leaves={}, inputs={p: hashlib.sha256(open(p, "rb").read()).hexdigest() for p in (tt, ff, pf)})
rows = []
for lf, v in T.items():
    if lf not in P["TT_leaf"]: continue
    mt = st.mean(x[0] for x in v) * (1000 if max(x[0] for x in v) < 5 else 1)
    mf = st.mean(min(x[2], x[3]) for x in F[lf]) * (1000 if max(x[2] for x in F[lf]) < 5 else 1)
    pt, pe = P["TT_leaf"][lf]["rise"], P["FF_leaf"][lf]["early"]
    rows.append((lf, mt, mf, pt, pe)); o["leaves"][lf] = dict(meas_TT_rise=round(mt, 2), meas_FF_early=round(mf, 2), pred_TT_rise=pt, pred_FF_early=pe)
def s(v): return dict(mean=round(st.mean(v), 2), min=round(min(v), 2), max=round(max(v), 2), window=round(max(v) - min(v), 2))
o["meas"] = dict(TT_rise=s([r[1] for r in rows]), FF_early=s([r[2] for r in rows]))
o["pred"] = dict(TT_rise=s([r[3] for r in rows]), FF_early=s([r[4] for r in rows]))
rt = [r[1] - r[3] for r in rows]; rf = [r[2] - r[4] for r in rows]
o["residual_meas_minus_pred"] = dict(TT=dict(mean=round(st.mean(rt), 2), sd=round(st.pstdev(rt), 2), min=round(min(rt), 2), max=round(max(rt), 2)),
                                     FF=dict(mean=round(st.mean(rf), 2), sd=round(st.pstdev(rf), 2), min=round(min(rf), 2), max=round(max(rf), 2)))
o["n_leaves"] = len(rows); o["scope"] = "HEAD-CORE-LAT-R5 CALIBRATION (non-gating), GRT RC, UNCHECKED"
json.dump(o, open(out, "w"), indent=1)
print("MEAS TT rise %(mean).2f w%(window).2f" % o["meas"]["TT_rise"], "| FF early %(mean).2f w%(window).2f" % o["meas"]["FF_early"],
      "| PRED TT %(mean).2f w%(window).2f" % o["pred"]["TT_rise"], "FF %(mean).2f w%(window).2f" % o["pred"]["FF_early"],
      "| RESID TT", o["residual_meas_minus_pred"]["TT"], "FF", o["residual_meas_minus_pred"]["FF"])
