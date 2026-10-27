#!/usr/bin/env python3
"""MODEL-REFIT-3 diagnostic: RCX-GRT TT-rise leaf shift aggregated per L1 island (first-level branch), vs island size
(leaves, sinks), routed vias and plan length on the root->island feed nets.  LSQ + leave-one-build-out.  UNCHECKED."""
import json, statistics as st, sys
import numpy as np
sys.path.insert(0, sys.path[0])
import uf_phys3 as V, points as PT
from uf_phys3 import U, common
rows = []
for b in ("vmr_f4a", "rp1_f4a", "btab_r5"):
    p = PT.POINTS[b]; P = V.load_plan(p["spec"], p["geo"], p["seg"])
    via = {ln.split("\t")[0]: int(ln.split("\t")[1]) for ln in open(p["vias_rcx"]) if not ln.startswith("#")}
    g = common.parse_sinks(p["grt"][0])[0]; r = common.parse_sinks(p["rcx"][0])[0]
    def path(k):
        o = []; x = k
        while P.nodes[x]["par"]: o.append(x); x = P.nodes[x]["par"]
        return o[::-1]
    isl = {}
    for k in g:
        pp = path(k); isl.setdefault(pp[0], []).append((k, pp))
    for a, ls in isl.items():
        # feed = nets from root down to the first node with fanout > 1 (the island driver), inclusive of its net
        feed, x = [], "root"
        nxt = a
        while True:
            feed.append(V.net_name(x))
            if len(P.kids.get(nxt, [])) != 1: feed.append(V.net_name(nxt)); break
            x, nxt = nxt, P.kids[nxt][0]
        fv = sum(via.get(n, 0) for n in feed[1:]); fl = sum(P._seglen(c) for c in [a] + [P.kids[c][0] for c in [a] if len(P.kids.get(c, [])) == 1])
        sinks = sum(len(P.nodes[k]["sinks"]) for k, _ in ls)
        sh = st.mean(r[k]["rise"] - g[k]["rise"] for k, _ in ls)
        rows.append(dict(build=b, island=a, leaves=len(ls), sinks=sinks, feed_vias=fv, shift=round(sh, 2)))
for x in sorted(rows, key=lambda x: x["shift"]): print(x)
def lsq(tr, cols):
    A = np.array([[1.0] + [x[c] for c in cols] for x in tr]); y = np.array([x["shift"] for x in tr])
    c, *_ = np.linalg.lstsq(A, y, rcond=None); return c
res = {}
for cols in (["leaves"], ["feed_vias"], ["leaves", "feed_vias"], ["sinks"]):
    c = lsq(rows, cols); e = []
    for h in ("vmr_f4a", "rp1_f4a", "btab_r5"):
        ch = lsq([x for x in rows if x["build"] != h], cols)
        e += [x["shift"] - (ch[0] + sum(ch[i + 1] * x[cc] for i, cc in enumerate(cols))) for x in rows if x["build"] == h]
    res["+".join(cols)] = dict(coef=[round(v, 4) for v in c], loo_island_err_sd=round(float(np.std(e)), 2), loo_island_err_max=round(float(np.max(np.abs(e))), 2))
    print(cols, res["+".join(cols)])
print("shift sd (no term)", round(float(np.std([x["shift"] for x in rows])), 2))
json.dump(dict(rows=rows, fits=res), open(sys.argv[1], "w"), indent=1)
