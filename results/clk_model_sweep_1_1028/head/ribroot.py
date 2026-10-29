"""spine rib-root arrival spread: measured vs predicted by length-only (the DME criterion) and by the per-leg fit."""
import json, sys, collections, numpy as np
G = sys.argv[1]; T = json.load(open(f"{G}/clk/tree.json"))
nodes = {int(k): v for k, v in T["nodes"].items()}; nb = {int(k): v for k, v in T["node_buf"].items()}
po, site = T["parent_of"], T["sites"]; ntap = collections.Counter(t["node"] for t in T["taps"])
man = lambda a, b: abs(a[0]-b[0]) + abs(a[1]-b[1])
fit = json.load(open(sys.argv[2]))
for C in ("TT", "FF"):
    c = fit[C]["coef_d0_k1_k2_kf"]
    arr = {p[1]: float(p[3]) for p in (l.split() for l in open(f"{G}/out_{C}/arr_{C}.txt")) if p[0] == "N"}
    leg = {}
    for i, nd in nodes.items():
        if nd["parent"] is None: continue
        bi, bp = nb[i], nb[nd["parent"]]; ch = [bi]; x = bi
        while x != bp: x = po[x]; ch.append(x)
        pts = [tuple(site[q]) for q in reversed(ch)]; segs = [man(a, b) for a, b in zip(pts, pts[1:])]
        fo = len(nd["kids"]) + ntap.get(i, 0)
        leg[i] = (sum(segs), c[0]*len(segs) + c[1]*sum(segs) + c[2]*sum(s*s for s in segs) + c[3]*(fo-1))
    def ps(i, k):
        t = 0.0
        while nodes[i]["parent"] is not None: t += leg[i][k]; i = nodes[i]["parent"]
        return t
    rr = [i for i, nd in nodes.items() if nd.get("spine") and nd["parent"] is not None and not any(nodes[k].get("spine") for k in nd["kids"])]
    M = np.array([arr[nb[i]] for i in rr]); Lp = np.array([ps(i, 0) for i in rr]); F = np.array([ps(i, 1) for i in rr])
    sp = lambda v: round(float(v.max() - v.min()), 1)
    print(C, "ribroots", len(rr), "meas spread", sp(M), "len spread um", sp(Lp), "fit-pred spread", sp(F),
          "meas-fit resid spread", sp(M - F))
    # all taps: per tap measured arrival vs fit path pred (rms)
    ta = {p[1]: float(p[3]) for p in (l.split() for l in open(f"{G}/out_{C}/arr_{C}.txt")) if p[0] == "T"}
