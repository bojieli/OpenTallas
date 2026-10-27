#!/usr/bin/env python3
"""QC-SU-PROG-L2: measured GRT per-leaf clock latency (meas_ck TSV) vs ht_l2 plan prediction (ht2.json phys, refit4).
usage: measresid.py TT.tsv FF.tsv HT2.json OUT.json   TT basis = rise (arrival max rise), FF basis = early (min(rise_min, fall_min - T/2))."""
import json, sys, statistics as st
tt, ff, h2, out = sys.argv[1:5]
P2 = 833.0 / 2
ph = json.load(open(h2))["phys"]
def taps(f):
    t = {}; mac = {}
    for ln in open(f):
        if ln.startswith("#"): continue
        pin, net, rM, fM, rm, fm = ln.rstrip("\n").split("\t")
        v = dict(rise=float(rM), early=min(float(rm), float(fm) - P2), late=max(float(rM), float(fM) - P2))
        if net.startswith("ot_ms_m") and net[7].isdigit(): mac[pin] = v; continue
        t.setdefault(net[len("ot_ms_"):-len("_clk")], []).append(v)
    return t, mac
res = dict(basis="STA per-sink CK arrival on GRT parasitics (meas_ck.tcl, rc_cal 0.8/0.9); pred = ht_l2 refit4 per-leaf", corners={})
for C, f, b in (("TT", tt, "rise"), ("FF", ff, "early")):
    t, mac = taps(f)
    pl = ph[C + "_leaf"]
    def pv(k):
        x = pl[k]; return x[b] if isinstance(x, dict) else x
    tm = {k: st.mean(x[b] for x in v) for k, v in t.items()}
    d = {k: tm[k] - pv(k) for k in tm}
    lm = {k: st.mean(x["late"] for x in v) for k, v in t.items()}
    res["corners"][C] = dict(basis=b, n=sum(len(v) for v in t.values()), leaves=len(tm),
        mean=round(st.mean(x[b] for v in t.values() for x in v), 2), tap_mean_window=round(max(tm.values()) - min(tm.values()), 2),
        pred_mean=ph[C + "_" + b]["mean"] if (C + "_" + b) in ph else None, pred_window=ph[C + "_" + b]["window"] if (C + "_" + b) in ph else None,
        late_mean=round(st.mean(x["late"] for v in t.values() for x in v), 2), late_window=round(max(lm.values()) - min(lm.values()), 2),
        resid=dict(mean=round(st.mean(d.values()), 2), sd=round(st.pstdev(d.values()), 2), min=round(min(d.values()), 2), max=round(max(d.values()), 2),
                   argmin=min(d, key=d.get), argmax=max(d, key=d.get)),
        macros={k: round(v[b], 2) for k, v in mac.items()},
        per_leaf={k: dict(meas=round(tm[k], 2), pred=round(pv(k), 2), resid=round(d[k], 2)) for k in sorted(tm)})
json.dump(res, open(out, "w"), indent=1)
for C, r in res["corners"].items():
    print(C, r["basis"], "mean", r["mean"], "win", r["tap_mean_window"], "pred", r["pred_mean"], r["pred_window"], "resid", r["resid"], "late", r["late_mean"], r["late_window"])
