#!/usr/bin/env python3
"""FLOW-RC-1 diagnostic: per-class (SIGNAL/CLOCK) per-net est-vs-RCX C and R, per-layer RCX unit-C/R fits by class.
usage: frc_compare.py <view_dir> <out.json> [net_regex]   (view_dir has wd/wire.tsv, est_tt/est_*.spef; RCX spef path in view_dir/rcx_spef)"""
import sys, os, re, json, glob, statistics as st
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rc_calib as rc
V, OUT = sys.argv[1], sys.argv[2]; rx = re.compile(sys.argv[3]) if len(sys.argv) > 3 else None
wire = {k.replace("\\", ""): v for k, v in rc.parse_wire(V + "/wd/wire.tsv").items()}
want = set(wire)
rcx = rc.parse_spef(open(V + "/rcx_spef").read().strip(), want)
def q(a, p): a = sorted(a); return a[min(len(a) - 1, int(p * len(a)))] if a else None
def stats(r):
    return None if not r else {"n": len(r), "median": round(st.median(r), 3), "mean": round(sum(r) / len(r), 3),
                                "p05": round(q(r, .05), 3), "p95": round(q(r, .95), 3)}
res = {"view": V, "nets_wire": len(wire), "nets_rcx": len(rcx)}
LAY = ["M2", "M3", "M4", "M5", "M6", "M7"]
for cls in ("SIGNAL", "CLOCK"):
    f = rc.fit_layers(wire, rcx, [L for L in LAY], 5.0, cls)
    if f:
        res["fit_" + cls] = {"C_fF_per_um": {k: round(v, 4) for k, v in f["C_fF_per_um"].items()},
                             "R_ohm_per_um": {k: round(v, 2) for k, v in f["R_ohm_per_um"].items()},
                             "C_fit": f["C_fit"], "n": f["C_fit"]["n"],
                             "len_um": {L: round(sum(a.get(L, 0) for n, (s, a) in wire.items() if s == cls), 1) for L in LAY}}
for e in sorted(glob.glob(V + "/est_tt/est_*.spef")):
    tag = os.path.basename(e)[4:-5]
    est = rc.parse_spef(e, want)
    d = {}
    for cls in ("SIGNAL", "CLOCK"):
        rC, rR, rCl, rRl = [], [], [], []
        for n, (s, acc) in wire.items():
            if s != cls or n not in est or n not in rcx: continue
            L = sum(v for k, v in acc.items() if not k.startswith("V@"))
            if L < 5 or rcx[n][0] <= 0: continue
            rC.append(est[n][0] / rcx[n][0])
            if rcx[n][1] > 0: rR.append(est[n][1] / rcx[n][1])
            if L >= 50:
                rCl.append(est[n][0] / rcx[n][0])
                if rcx[n][1] > 0: rRl.append(est[n][1] / rcx[n][1])
        d[cls] = {"C_est_over_rcx": stats(rC), "C_est_over_rcx_len_ge50um": stats(rCl), "R_est_over_rcx": stats(rR), "R_est_over_rcx_len_ge50um": stats(rRl)}
    if rx:
        d["probe_nets"] = {n: {"len": round(sum(v for k, v in wire[n][1].items() if not k.startswith("V@")), 1),
                               "layers": {k: round(v, 1) for k, v in wire[n][1].items() if not k.startswith("V@")},
                               "C_est": round(est.get(n, (0, 0))[0], 2), "C_rcx": round(rcx[n][0], 2),
                               "R_est": round(est.get(n, (0, 0))[1], 1), "R_rcx": round(rcx[n][1], 1)}
                           for n in list(filter(rx.search, wire))[:12] if n in rcx}
    res["est_" + tag] = d
json.dump(res, open(OUT, "w"), indent=1)
print(json.dumps(res, indent=1))
