#!/usr/bin/env python3
"""DIE-S81-9 ESTIMATE (12.14b, diagnostic, no build): on the Codex packed-G routed clock (GRT RC, OpenSTA arrivals),
fit the routed region-DME leg delay d = n*d0 + k1*L + k2*L^2/n per corner, then per DME region:
  routed range (taps), fit-predicted range on the as-built tree (systematic part a fit-model DME rebuild balances out),
  residual range = range(routed - fitpred)  (estimate of the post-rebuild in-region range, assumes DME balances the fit to ~0).
Also neighbour-tap pairs (<200 um, same region): mean |d routed| vs mean |d residual|.
  est_fit_all.py TREE ARR_JSON CORNER OUT_JSON"""
import json, sys, math, collections
import numpy as np
T, AJ, C, OUT = sys.argv[1:5]
t = json.load(open(T)); N = {int(k): v for k, v in t["nodes"].items()}
A = json.load(open(AJ)); L = A["node_late_ps"]; ST = A["node_stages"]
path = {0: "h"}; st = [0]
while st:
    i = st.pop()
    for k, c in enumerate(N[i]["kids"]):
        path[c] = path[i] + str(k); st.append(c)
def leglen(i):
    nd = N[i]; pa = N[nd["parent"]]; r = nd.get("route")
    if r: return sum(abs(r[j+1][0]-r[j][0]) + abs(r[j+1][1]-r[j][1]) for j in range(len(r)-1))
    return abs(nd["x"]-pa["x"]) + abs(nd["y"]-pa["y"])
rows = []
for i, nd in N.items():
    if "dme" not in nd or nd["parent"] is None: continue
    p, q = path.get(i), path.get(nd["parent"])
    if p not in L or q not in L: continue
    n = ST[p] - ST[q]
    if n < 1: continue
    rows.append((n, leglen(i), L[p] - L[q]))
R = np.array(rows, float); n, Ln, d = R[:, 0], R[:, 1], R[:, 2]
X = np.stack([n, Ln, Ln*Ln/n], 1); coef, *_ = np.linalg.lstsq(X, d, rcond=None); res = d - X @ coef
fit = lambda nn, LL: nn*coef[0] + coef[1]*LL + coef[2]*LL*LL/max(nn, 1)
def acc(i):
    s = 0.0
    while "dme" in N[i] and N[i]["parent"] is not None:
        pi = N[i]["parent"]; s += fit(ST[path[i]] - ST[path[pi]], leglen(i)); i = pi
    return s, i
by = collections.defaultdict(list)
for x in A["taps"]:
    fp, top = acc(x["node"]); by[x["part"]].append((x["late_ps"], fp, x["xy_um"], top))
out = {}; nb_r = []; nb_s = []
for R_, v in by.items():
    if len(v) < 2: continue
    r = [a for a, _, _, _ in v]; f = [b for _, b, _, _ in v]; s = [a - b for a, b, _, _ in v]
    out[R_] = dict(ntaps=len(v), routed=max(r)-min(r), fitpred=max(f)-min(f), resid=max(s)-min(s))
    for i in range(len(v)):
        for j in range(i+1, len(v)):
            if abs(v[i][2][0]-v[j][2][0]) + abs(v[i][2][1]-v[j][2][1]) < 200:
                nb_r.append(abs(r[i]-r[j])); nb_s.append(abs(s[i]-s[j]))
vals = list(out.values())
def q(k, p): return float(np.percentile([x[k] for x in vals], p))
summ = dict(corner=C, legs=len(rows), fit=[float(c) for c in coef], fit_rms=float(res.std()), regions=len(vals),
            routed_max=q("routed", 100), routed_p90=q("routed", 90), routed_med=q("routed", 50),
            resid_max=q("resid", 100), resid_p90=q("resid", 90), resid_med=q("resid", 50),
            n_routed_gt100=sum(x["routed"] > 100 for x in vals), n_resid_gt100=sum(x["resid"] > 100 for x in vals),
            nb_pairs=len(nb_r), nb_routed_mean=float(np.mean(nb_r)), nb_routed_p99=float(np.percentile(nb_r, 99)), nb_routed_max=float(max(nb_r)),
            nb_resid_mean=float(np.mean(nb_s)), nb_resid_p99=float(np.percentile(nb_s, 99)), nb_resid_max=float(max(nb_s)))
worst = sorted(out.items(), key=lambda kv: -kv[1]["routed"])[:12]
json.dump(dict(summary=summ, worst=worst, regions=out), open(OUT, "w"), indent=1, default=float)
print(json.dumps(summ, indent=1, default=float)); [print(k, {a: round(b, 1) for a, b in v.items()}) for k, v in worst]
