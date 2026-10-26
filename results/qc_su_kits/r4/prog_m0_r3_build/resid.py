#!/usr/bin/env python3
"""QC-SU-KITS-3: measured (STA per-sink TSV, meas_ck.tcl) vs as-built prediction per leaf. usage: resid.py TT.tsv FF.tsv ASBUILT.json OUT.json"""
import json, sys, statistics as st
tt, ff, asb, out = sys.argv[1:5]
P2 = 833.0 / 2
A = json.load(open(asb))
OFF = {"TT": 1.9, "FF": -5.1}
res = dict(basis="STA per-sink CK arrival on GRT parasitics (estimate_parasitics -global_routing, rc_cal 0.8/0.9), "
                 "propagated clock; rise = arrival_*_rise, fall = arrival_*_fall - T/2; late = max(rise_max, fall_max), "
                 "early = min(rise_min, fall_min); tap = clock net ot_ms_<leaf>_clk (macro: ot_ms_m<k>_clk)",
           inputs=dict(tt=tt, ff=ff, asbuilt=asb), corners={})
for C, f in (("TT", tt), ("FF", ff)):
    taps = {}
    mac = {}
    for ln in open(f):
        if ln.startswith("#"):
            continue
        pin, net, rM, fM, rm, fm = ln.rstrip("\n").split("\t")
        rM, fM, rm, fm = float(rM), float(fM) - P2, float(rm), float(fm) - P2
        v = dict(rise_max=rM, late=max(rM, fM), early=min(rm, fm), rise_min=rm)
        if net.startswith("ot_ms_m") and net[7].isdigit():
            mac[pin] = v
            continue
        leaf = net[len("ot_ms_"):-len("_clk")]
        taps.setdefault(leaf, []).append(v)
    cr = {}
    for basis in ("rise_max", "late", "early", "rise_min"):
        tm = {k: st.mean(x[basis] for x in v) for k, v in taps.items()}
        allv = [x[basis] for v in taps.values() for x in v]
        pred_key = {"rise_max": None, "late": "late", "early": "early", "rise_min": None}[basis]
        pl = A["leaf"][C]["leaf"]
        d = [tm[k] - (pl[k] + OFF[C]) for k in tm]
        cr[basis] = dict(n=len(allv), mean=round(st.mean(allv), 2), min=round(min(allv), 2), max=round(max(allv), 2),
                         tap_mean_window=round(max(tm.values()) - min(tm.values()), 2),
                         tap_mean_min=round(min(tm.values()), 2), tap_mean_max=round(max(tm.values()), 2),
                         resid_vs_asbuilt_avg_model=dict(mean=round(st.mean(d), 2), sd=round(st.pstdev(d), 2),
                                                         min=round(min(d), 2), max=round(max(d), 2)))
        if basis in ("rise_max", "early"):
            cr[basis]["per_leaf"] = {k: dict(meas=round(tm[k], 2), pred=round(pl[k] + OFF[C], 2),
                                             resid=round(tm[k] - pl[k] - OFF[C], 2)) for k in sorted(tm)}
    el = A["early_late"][C]
    cr["pred_asbuilt"] = dict(avg=A["asbuilt"][C], early=el["early"], late=el["late"])
    cr["macro_ck"] = {k: round(v["rise_max"], 2) for k, v in mac.items()}
    res["corners"][C] = cr
json.dump(res, open(out, "w"), indent=1)
for C in ("TT", "FF"):
    cr = res["corners"][C]
    for b in ("rise_max", "late", "early"):
        x = cr[b]
        print(C, b, "mean", x["mean"], "range", x["min"], x["max"], "tapwin", x["tap_mean_window"], "resid", x["resid_vs_asbuilt_avg_model"])
    print(C, "pred", {k: (v["mean"], v["window"]) for k, v in cr["pred_asbuilt"].items()}, "macro", cr["macro_ck"])
