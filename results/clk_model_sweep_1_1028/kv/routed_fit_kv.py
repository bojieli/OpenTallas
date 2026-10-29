"""KV: does routed layer/length explain the per-leg residual the placed-geometry stage fit leaves?  Leg features from GRT
route guides (per-layer guide length of every net in the leg chain; parent node net is shared with siblings).  usage: DIR"""
import json, sys, collections, numpy as np
D = sys.argv[1]
T = json.load(open(f"{D}/tree.json")); nodes = {int(k): v for k, v in T["nodes"].items()}
nb = {int(k): v for k, v in T["node_buf"].items()}; site, par = T["sites"], T["parent_of"]
ntap = collections.Counter(t["node"] for t in T["taps"])
md = lambda a, b: abs(a[0] - b[0]) + abs(a[1] - b[1])
onet = lambda c: "ck_n" + c[1:] if c[0] == "b" else "ck_rn" + c[1:]
for C in ("TT", "FF"):
    G = json.load(open(f"{D}/glay_{C}.json"))
    arr = {p[1]: float(p[2]) for p in (l.split() for l in open(f"{D}/arr_{C}.txt")) if p[0] == "N"}
    X = []
    for i, nd in nodes.items():
        if nd["parent"] is None or nd.get("feed"): continue
        cb, pb = nb[i], nb[nd["parent"]]
        ch = [cb]
        while ch[-1] != pb: ch.append(par[ch[-1]])
        ch = ch[::-1]
        segs = [md(site[a], site[b]) for a, b in zip(ch, ch[1:])]
        m8 = sum(G.get(onet(c), {}).get("M8", 0) for c in ch[:-1]) / 1e3
        m9 = sum(G.get(onet(c), {}).get("M9", 0) for c in ch[:-1]) / 1e3
        oth = sum(v for c in ch[:-1] for z, v in G.get(onet(c), {}).items() if z not in ("M8", "M9")) / 1e3
        fo = len(nd["kids"]) + ntap.get(i, 0)
        X.append([len(segs), sum(segs), sum(s * s for s in segs), fo - 1, m8, m9, oth, arr[cb] - arr[pb]])
    X = np.array(X); y = X[:, -1]
    def r(cols):
        c, *_ = np.linalg.lstsq(X[:, cols], y, rcond=None); e = y - X[:, cols] @ c
        return round(float(np.sqrt((e ** 2).mean())), 2), [round(float(v), 5) for v in c]
    print(C, "legs", len(X), "placed n,L,Ls2,fo:", r([0, 1, 2, 3]), " +routed M8,M9,other:", r([0, 1, 2, 3, 4, 5, 6]),
          " n,fo,M8,M9 only:", r([0, 3, 4, 5]), " frac legs with M8 only (no M9):",
          round(float(((X[:, 5] == 0) & (X[:, 4] > 0)).mean()), 3))
