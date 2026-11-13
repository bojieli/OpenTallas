"""HOLD-TAP-1: per-leg routed delay vs model by leg category on a routed DME kit. usage: legcat.py TOOLS KIT ARR_PREFIX OUT.json"""
import json, sys, math, statistics as st
from collections import defaultdict
import numpy as np
sys.path.insert(0, sys.argv[1])
import die_trial as D
K, A, OUT = sys.argv[2:5]
T = json.load(open(f"{K}/clock/tree.json"))
nodes = {int(k): v for k, v in T["nodes"].items()}; nb = {int(k): v for k, v in T["node_buf"].items()}
ntap = defaultdict(int)
for t in T["taps"]: ntap[t["node"]] += 1
arr = {}
for C in ("TT", "FF"):
    a = {}
    for l in open(f"{A}_{C}/arr_{C}.txt"):
        p = l.split()
        if p[0] == "N": a[p[1]] = float(p[2])
        elif p[0] == "T": a["port:" + p[1]] = float(p[2])
    arr[C] = a
rep = 250.0
def segs_of(i):
    nd = nodes[i]; p = nodes[nd["parent"]]; pa, q = (p["x"], p["y"]), (nd["x"], nd["y"])
    if nd.get("snake"):
        pts = [pa] + [tuple(x) for x in nd["snake"]] + [q]
        return [D._man(a, b) for a, b in zip(pts, pts[1:])], "snake"
    pts = [tuple(x) for x in nd["route"]] if nd.get("route") else [pa, q]
    L = sum(D._man(a, b) for a, b in zip(pts, pts[1:]))
    n = max(1, math.ceil(L / rep - 1e-9)); n += n % 2
    return [L / n] * n, ("route" if nd.get("route") else "plain")
legs = [i for i, nd in nodes.items() if nd.get("dme") and nd.get("parent") is not None and nb.get(i) in arr["TT"] and nb.get(nodes[i]["parent"]) in arr["TT"]]
rows = []
for i in legs:
    s, cat = segs_of(i); fo = len(nodes[i]["kids"]) + ntap[i]
    geo = D._man((nodes[nodes[i]["parent"]]["x"], nodes[nodes[i]["parent"]]["y"]), (nodes[i]["x"], nodes[i]["y"]))
    rows.append(dict(i=i, cat=cat, n=len(s), L=sum(s), L2=sum(x * x for x in s), fo=fo - 1, geo=geo,
                     TT=arr["TT"][nb[i]] - arr["TT"][nb[nodes[i]["parent"]]], FF=arr["FF"][nb[i]] - arr["FF"][nb[nodes[i]["parent"]]],
                     keys=[k for k in nodes[i] if k not in ("x", "y", "kids", "parent", "snake", "route")]))
print("legs", len(rows), "by cat", {c: sum(r["cat"] == c for r in rows) for c in ("plain", "route", "snake")})
print("node keys sample", rows[0]["keys"], [r["keys"] for r in rows if r["cat"] == "snake"][:1])
def fit(R, C):
    X = np.array([[r["n"], r["L"], r["L2"], r["fo"]] for r in R]); y = np.array([r[C] for r in R])
    c, *_ = np.linalg.lstsq(X, y, rcond=None); res = y - X @ c
    return c, res
out = {}
for C in ("TT", "FF"):
    c, res = fit(rows, C)
    print(C, "ALL fit", np.round(c, 6), "resid sd %.1f p01 %.1f p99 %.1f" % (res.std(), np.percentile(res, 1), np.percentile(res, 99)))
    for cat in ("plain", "route", "snake"):
        R = [r for r in rows if r["cat"] == cat]
        if len(R) < 10: continue
        idx = [k for k, r in enumerate(rows) if r["cat"] == cat]
        rr = res[idx]; cc, r2 = fit(R, C)
        ratio = np.array([r["L"] / max(r["geo"], 1.0) for r in R])
        print("  ", cat, len(R), "resid under the ALL fit: mean %.1f sd %.1f" % (rr.mean(), rr.std()), "| own fit", np.round(cc, 6), "own resid sd %.1f" % r2.std(),
              "| L/geo p50 %.2f max %.1f ; delay per um p50 %.3f ; L p50 %.0f n p50 %d" % (np.median(ratio), ratio.max(), np.median([r[C] / max(r["L"], 1) for r in R]), np.median([r["L"] for r in R]), np.median([r["n"] for r in R])))
        out[f"{cat}_{C}"] = [float(x) for x in cc]
    out[f"all_{C}"] = [float(x) for x in c]
json.dump(out, open(OUT, "w"), indent=0)
