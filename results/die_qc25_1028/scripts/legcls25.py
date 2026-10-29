#!/usr/bin/env python3
"""DIE-QC-25 task 4: per-class region-DME leg model on routed legs (trial24 == trial14), uses the shared fitter's leg_rows.
Classes: snake / plain straight / plain routed (L-route or detour).  Reports per-leg rms and the per-TAP accumulated
residual (sum of leg residuals from the region root down to the tap's node) for: built model, global refit, per-class
refit; per-class also on a 2-fold region split (fit on even regions, score odd and vice versa) to show it is not overfit.
usage: legcls25.py TREE ARR_PREFIX BUILT_CAL OUT"""
import json, sys, collections
import numpy as np
sys.path.insert(0, sys.argv[5] if len(sys.argv) > 5 else ".")
import fit_dme_stage_cal as F
tree = json.load(open(sys.argv[1])); built = json.load(open(sys.argv[3]))
nodes = {int(k): v for k, v in tree["nodes"].items()}
def cls(i):
    nd = nodes[i]
    return "snake" if nd.get("snake") else ("routed" if nd.get("route") and len(nd["route"]) > 2 else "straight")
def region(i):
    while nodes[i].get("parent") is not None and nodes[nodes[i]["parent"]].get("dme"):
        i = nodes[i]["parent"]
    return i
out = {}
for C in ("TT", "FF"):
    arr = F.read_node_early(f"{sys.argv[2]}_{C}/arr_{C}.txt")
    rows = F.leg_rows(tree, arr, 250.0, True)
    ids = [r[0] for r in rows]; X = np.array([r[1] for r in rows], float); y = np.array([r[2] for r in rows], float)
    K = np.array([cls(i) for i in ids]); R = np.array([region(i) for i in ids])
    fold = np.array([hash(int(r)) % 2 for r in R])
    bc = np.array(built["leg" if C == "TT" else "leg_FF"], float)
    preds = {"built": X @ bc}
    g, *_ = np.linalg.lstsq(X, y, rcond=None); preds["global"] = X @ g
    pc = np.zeros_like(y); pcx = np.zeros_like(y); coefs = {}
    for k in sorted(set(K)):
        m = K == k
        c, *_ = np.linalg.lstsq(X[m], y[m], rcond=None); pc[m] = X[m] @ c; coefs[k] = [round(float(v), 6) for v in c]
        for f in (0, 1):
            tr, te = m & (fold != f), m & (fold == f)
            c2, *_ = np.linalg.lstsq(X[tr], y[tr], rcond=None); pcx[te] = X[te] @ c2
    preds["per_class"] = pc; preds["per_class_2fold"] = pcx
    res = {}
    rid = dict(zip(ids, range(len(ids))))
    taps_nodes = collections.Counter(t["node"] for t in tree.get("taps", []))
    for name, p in preds.items():
        r = y - p
        acc = {}
        def tap_err(i):
            if i in acc: return acc[i]
            e = r[rid[i]] if i in rid else 0.0
            par = nodes[i].get("parent")
            v = e + (tap_err(par) if par is not None and nodes[par].get("dme") else 0.0)
            acc[i] = v; return v
        te = np.array([tap_err(n) for n in taps_nodes for _ in range(taps_nodes[n]) if n in nodes])
        # per region: spread of accumulated error across its taps (what skew sees)
        byreg = collections.defaultdict(list)
        for n in taps_nodes:
            if n in nodes: byreg[region(n)].append(tap_err(n))
        spread = np.array([max(v) - min(v) for v in byreg.values() if len(v) > 1])
        res[name] = dict(leg_rms=round(float(np.sqrt((r ** 2).mean())), 2),
                         leg_rms_by_class={k: round(float(np.sqrt((r[K == k] ** 2).mean())), 2) for k in sorted(set(K))},
                         tap_abs_err_p50_p90_p99=[round(float(np.percentile(np.abs(te), q)), 1) for q in (50, 90, 99)],
                         region_tap_err_spread_p50_p90_max=[round(float(np.percentile(spread, q)), 1) for q in (50, 90)] + [round(float(spread.max()), 1)])
    out[C] = dict(legs=len(rows), class_counts=dict(collections.Counter(K.tolist())), coef_per_class=coefs,
                  coef_global=[round(float(v), 6) for v in g], models=res)
json.dump(out, open(sys.argv[4], "w"), indent=1)
for C in out:
    print(C, out[C]["class_counts"], out[C]["coef_per_class"])
    for k, v in out[C]["models"].items(): print(" ", C, k, v)
