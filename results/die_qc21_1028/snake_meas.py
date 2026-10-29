"""DIE-QC-21: modelled vs routed clock leg delay per leg class in c_* (merge-mode) and su_c (hang) DME regions.
usage: snake_meas.py TOOLS_DIR TRIAL_DIR ARR_PREFIX OUT.json"""
import json, sys, math, statistics as st
from collections import defaultdict
sys.path.insert(0, sys.argv[1])
import die_trial as D
K, A, OUT = sys.argv[2], sys.argv[3], sys.argv[4]
T = json.load(open(f"{K}/clock/tree.json"))
nodes = {int(k): v for k, v in T["nodes"].items()}
nb = {int(k): v for k, v in T["node_buf"].items()}
D.EVEN_LEGS = True  # inv2
arr = {}
for C in ("TT", "FF"):
    a = {}
    for ln in open(f"{A}_{C}/arr_{C}.txt"):
        p = ln.split()
        if p[0] == "N":
            a[p[1]] = float(p[2])
        elif p[0] == "T":
            a["port:" + p[1]] = float(p[2])
    arr[C] = a
rep = T["meta"].get("rep_um", 250.0)
rows = []
for i, nd in nodes.items():
    rn = nd.get("dme")
    if not rn or nd.get("parent") is None:
        continue
    p = nodes[nd["parent"]]
    pa, q = (p["x"], p["y"]), (nd["x"], nd["y"])
    if nd.get("snake"):
        cls = "snake"
        model = D.chain_ps([pa] + [tuple(x) for x in nd["snake"]] + [q])
        L = sum(D._man(a, b) for a, b in zip([pa] + [tuple(x) for x in nd["snake"]], [tuple(x) for x in nd["snake"]] + [q]))
    else:
        cls = "plain"
        pts = [tuple(x) for x in nd["route"]] if nd.get("route") else [pa, q]
        L = sum(D._man(a, b) for a, b in zip(pts, pts[1:]))
        model = D.leg_ps(L, rep)
    r = {}
    for C in ("TT", "FF"):
        ca, pa_ = arr[C].get(nb.get(i)), arr[C].get(nb.get(nd["parent"]))
        r[C] = None if ca is None or pa_ is None else ca - pa_
    if r["TT"] is None:
        continue
    kind = "c" if rn.startswith("c_") else ("su_c" if rn.startswith("su_c") else "other")
    rows.append(dict(node=i, region=rn, kind=kind, cls=cls, L=round(L, 1), model=round(model, 2),
                     TT=round(r["TT"], 2), FF=None if r["FF"] is None else round(r["FF"], 2)))
summ = {}
g = defaultdict(list)
for r in rows:
    g[(r["kind"], r["cls"])].append(r)
for (k, c), rs in sorted(g.items()):
    m = sum(x["model"] for x in rs)
    tt = sum(x["TT"] for x in rs)
    ff = sum(x["FF"] for x in rs if x["FF"] is not None)
    rat = [x["TT"] / x["model"] for x in rs if x["model"] > 0]
    summ[f"{k}/{c}"] = dict(n=len(rs), model_sum=round(m, 1), TT_sum=round(tt, 1), FF_sum=round(ff, 1),
                            ratio_TT=round(tt / m, 4), ratio_FF=round(ff / m, 4),
                            ratio_TT_med=round(st.median(rat), 4), L_med=st.median(x["L"] for x in rs))
json.dump(dict(summary=summ, rows=rows), open(OUT, "w"), indent=0)
print(json.dumps(summ, indent=1))
