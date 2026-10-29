#!/usr/bin/env python3
"""DIE-S81-7: fit the routed per-leg delay of kit F's region-DME legs (combo GRT RC, OpenSTA arrivals) to the die_trial
leg_ps form d = n*d0 + k1*L + k2*L^2/n, and re-price the fE3_p2_b0 / fE2_p2_b0 region trees with model vs fit."""
import json, sys, math
import numpy as np
O = sys.argv[1]; V = sys.argv[2]; C = sys.argv[3] if len(sys.argv) > 3 else "TT"
t = json.load(open(f"{O}/clk_{V}/tree.json")); N = {int(k): v for k, v in t["nodes"].items()}
A = json.load(open(f"{O}/proof_{V}/tap_arrivals_{C}.json")); L = A["node_late_ps"]; XY = A["node_xy_um"]; ST = A["node_stages"]
# node id -> path: match by xy among kids order
path = {0: "h"}
stack = [0]
while stack:
    i = stack.pop()
    for k, c in enumerate(N[i]["kids"]):
        p = path[i] + str(k)
        path[c] = p
        stack.append(c)
chk = sum(1 for i, p in path.items() if p in XY and abs(XY[p][0] - N[i]["x"]) < 1 and abs(XY[p][1] - N[i]["y"]) < 1)
print("path map check", chk, "of", sum(1 for p in path.values() if p in XY))
def leglen(i):
    nd = N[i]; pa = N[nd["parent"]]
    r = nd.get("route")
    if r:
        return sum(abs(r[j+1][0]-r[j][0]) + abs(r[j+1][1]-r[j][1]) for j in range(len(r)-1))
    return abs(nd["x"]-pa["x"]) + abs(nd["y"]-pa["y"])
rows = []
for i, nd in N.items():
    if "dme" not in nd or nd["parent"] is None: continue
    p, q = path.get(i), path.get(nd["parent"])
    if p not in L or q not in L: continue
    n = ST[p] - ST[q]
    if n < 1: continue
    rows.append((nd["dme"], i, n, leglen(i), L[p] - L[q]))
R = np.array([(r[2], r[3], r[4]) for r in rows])
n, Ln, d = R[:, 0], R[:, 1], R[:, 2]
X = np.stack([n, Ln, Ln * Ln / n], 1)
coef, *_ = np.linalg.lstsq(X, d, rcond=None)
res = d - X @ coef
d0, k1, k2 = 20.8281, 0.013984, 0.00033554
mod = n * d0 + k1 * Ln + k2 * Ln * Ln / n
print("legs", len(rows), "fit d0 k1 k2", [round(float(c), 6) for c in coef], "resid rms %.2f max %.1f" % (res.std(), abs(res).max()))
print("model resid (routed - model) mean %.2f rms %.2f" % ((d - mod).mean(), (d - mod).std()))
for nn in (1, 2, 3, 4, 6):
    m = n == nn
    if m.sum(): print(" n=%d legs %d mean L %.0f routed %.1f model %.1f fit %.1f" % (nn, m.sum(), Ln[m].mean(), d[m].mean(), mod[m].mean(), (X @ coef)[m].mean()))
json.dump(dict(corner=C, fit=[float(c) for c in coef], legs=len(rows), rms=float(res.std())), open(f"{sys.argv[4] if len(sys.argv)>4 else '/tmp'}/stage_fit_{V}_{C}.json", "w"))
# per region: routed spread vs fit-predicted spread vs model spread (taps' arrival below region DME root)
for R_ in ("fE3_p2_b0", "fE2_p2_b0", "fE2_p5_b0", "gunit"):
    taps = [x for x in t["taps"] if x["part"] == R_]
    def acc(i, f):
        s = 0.0
        while "dme" in N[i] and N[i]["parent"] is not None and "dme" in N[N[i]["parent"]] or ("dme" in N[i] and N[i]["parent"] is not None):
            pi = N[i]["parent"]
            if "dme" not in N[i]: break
            p, q = path[i], path[pi]
            nn_ = ST[p] - ST[q]; LL = leglen(i)
            s += f(nn_, LL)
            i = pi
        return s
    fm = lambda nn_, LL: nn_ * d0 + k1 * LL + k2 * LL * LL / max(nn_, 1)
    ff = lambda nn_, LL: nn_ * coef[0] + coef[1] * LL + coef[2] * LL * LL / max(nn_, 1)
    vm = [acc(x["node"], fm) for x in taps]; vf = [acc(x["node"], ff) for x in taps]
    tl = {x["port"]: x["late_ps"] for x in A["taps"]}
    vr = [tl[x["port"]] for x in taps]
    print(R_, "ntaps", len(taps), "range routed %.1f  model %.1f  fit %.1f" % (max(vr) - min(vr), max(vm) - min(vm), max(vf) - min(vf)))
