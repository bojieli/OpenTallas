"""DIE-QC-21: fit routed leg delay (TT/FF) of inv2 DME legs to stage features. usage: fit.py TOOLS TRIAL ARR_PREFIX"""
import json, sys, math
import numpy as np
sys.path.insert(0, sys.argv[1])
import die_trial as D
K, A = sys.argv[2], sys.argv[3]
D.EVEN_LEGS = True
T = json.load(open(f"{K}/clock/tree.json"))
nodes = {int(k): v for k, v in T["nodes"].items()}
nb = {int(k): v for k, v in T["node_buf"].items()}
rep = 250.0
ntap = {}
for t in T["taps"]:
    ntap[t["node"]] = ntap.get(t["node"], 0) + 1
arr = {}
for C in ("TT", "FF"):
    arr[C] = {p[1]: float(p[2]) for p in (l.split() for l in open(f"{A}_{C}/arr_{C}.txt")) if p[0] == "N"}
X, Y, M, G = [], {"TT": [], "FF": []}, [], []
for i, nd in nodes.items():
    if not nd.get("dme") or nd.get("parent") is None: continue
    p = nodes[nd["parent"]]
    pa, q = (p["x"], p["y"]), (nd["x"], nd["y"])
    if nd.get("snake"):
        pts = [pa] + [tuple(x) for x in nd["snake"]] + [q]
        segs = [D._man(a, b) for a, b in zip(pts, pts[1:])]; m = D.chain_ps(pts); cls = 1
    else:
        pts = [tuple(x) for x in nd["route"]] if nd.get("route") else [pa, q]
        L = sum(D._man(a, b) for a, b in zip(pts, pts[1:]))
        n = max(1, math.ceil(L / rep - 1e-9)); n += n % 2
        segs = [L / n] * n; m = D.leg_ps(L, rep); cls = 0
    a, b = arr["TT"].get(nb[i]), arr["TT"].get(nb[nd["parent"]])
    if a is None or b is None: continue
    fo = len(nd["kids"]) + ntap.get(i, 0)
    # parent fanout: the parent drives this leg AND its siblings (first stage load)
    pfo = len(p["kids"]) + ntap.get(nd["parent"], 0)
    X.append([len(segs), sum(segs), sum(s * s for s in segs), fo, pfo - 1])
    for C in ("TT", "FF"):
        Y[C].append(arr[C][nb[i]] - arr[C][nb[nd["parent"]]])
    M.append(m); G.append(cls)
X = np.array(X, float); M = np.array(M); G = np.array(G)
for C in ("TT", "FF"):
    y = np.array(Y[C])
    for name, cols in (("3par n,L,L2", [0, 1, 2]), ("+fanout", [0, 1, 2, 3]), ("+fanout+sib", [0, 1, 2, 3, 4])):
        Xa = X[:, cols]
        c, *_ = np.linalg.lstsq(Xa, y, rcond=None)
        r = y - Xa @ c
        print(C, name, "coef", np.round(c, 6), "rms", round(float(np.sqrt((r ** 2).mean())), 2),
              "resid plain/snake mean", round(float(r[G == 0].mean()), 2), round(float(r[G == 1].mean()), 2))
    rr = y / M
    print(C, "ratio routed/model plain med", round(float(np.median(rr[G == 0])), 3), "snake", round(float(np.median(rr[G == 1])), 3))
    # ratio by node fanout
    for f in sorted(set(X[:, 3].astype(int)))[:8]:
        s = X[:, 3] == f
        print("   fo", f, "n", int(s.sum()), "ratio med", round(float(np.median(rr[s])), 3))
