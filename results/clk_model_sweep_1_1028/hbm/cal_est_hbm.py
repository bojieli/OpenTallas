"""CLK-MODEL-SWEEP-1 HBM: trial2b link_htree (geometric H-tree, no delay model). Per tree leg (node buf -> parent node buf
via parent_of cell chain): n stages, L, sum Ls^2, fanout-1 vs routed GRT N-row arrival diff (early=p[3]; late=p[2] too).
BEFORE = equal-length-equal-delay: residual around mean of matched group (rib region, level); feed legs: own group per feed_edge+level.
AFTER = LSQ fit n*d0+k1 L+k2 sumLs2+kf(fo-1).  Region pair error = max-min over taps of cumulative residual from region root.
usage: TREE ARR_DIR OUT"""
import json, sys, collections, math
import numpy as np
TR, AD, OUT = sys.argv[1:4]
T = json.load(open(TR))
nodes = {int(k): v for k, v in T["nodes"].items()}
nb = {int(k): v for k, v in T["node_buf"].items()}
inv_nb = {v: k for k, v in nb.items()}
po, S = T["parent_of"], T["sites"]
ntap = collections.Counter(t["node"] for t in T["taps"])
man = lambda a, b: abs(a[0]-b[0]) + abs(a[1]-b[1])
def region_of(i):
    n = i
    while n is not None:
        nd = nodes[n]
        if nd.get("rib"): return nd["rib"]
        if nd.get("region_root"): return nd["region_root"]
        n = nd["parent"]
    return None
res = {}
for C in ("TT", "FF"):
    rows_all = [l.split() for l in open(f"{AD}/c_{C}/arr_{C}.txt")]
    out = {}
    for col, nm in ((3, "early"), (2, "late")):
        arr = {p[1]: float(p[col]) for p in rows_all if p[0] == "N"}
        rows, ids, grp = [], [], []
        for i, nd in nodes.items():
            if nd["parent"] is None: continue
            pb = nb[nd["parent"]]; c = nb[i]; chain = [c]
            while c != pb and c in po:
                c = po[c]; chain.append(c)
            if c != pb: continue
            segs = [man(S[a], S[b]) for a, b in zip(chain, chain[1:])]
            a, b = arr.get(nb[i]), arr.get(pb)
            if a is None or b is None: continue
            fo = len(nd["kids"]) + ntap.get(i, 0)
            rows.append([len(segs), sum(segs), sum(s*s for s in segs), max(fo-1, 0), a-b]); ids.append(i)
            grp.append((nd.get("rib") or nd.get("feed_edge") or "?", nd["level"]))
        X = np.array(rows, float)
        c, *_ = np.linalg.lstsq(X[:, :4], X[:, 4], rcond=None)
        rc = X[:, 4] - X[:, :4] @ c
        gm = collections.defaultdict(list)
        for g, v in zip(grp, X[:, 4]): gm[g].append(v)
        mean = {g: np.mean(v) for g, v in gm.items()}
        rb = np.array([v - mean[g] for g, v in zip(grp, X[:, 4])])
        multi = np.array([len(gm[g]) > 1 for g in grp])
        rib = np.array([nodes[i].get("rib") is not None for i in ids])
        # residual rms restricted to rib legs in multi-leg groups (where the equal-length assumption is a real claim)
        msk = multi & rib
        E = {"before": dict(zip(ids, rb)), "after": dict(zip(ids, rc))}
        meas = {i: arr[nb[i]] for i in nodes if nb[i] in arr}
        cum = {}
        def cumf(i, e):
            key = (i, id(e))
            if key in cum: return cum[key]
            nd = nodes[i]
            if nd["parent"] is None or nd.get("region_root") or nd.get("feed"):
                v = 0.0     # region root/feed = reference (feed not balanced by design)
            else:
                v = cumf(nd["parent"], e) + e.get(i, 0.0)
            cum[key] = v; return v
        sys.setrecursionlimit(100000)
        byp = collections.defaultdict(list)
        for t in T["taps"]: byp[(region_of(t["node"]), t["part"])].append(t["node"])
        reg = {}
        for (r, p), ns in byp.items():
            d = reg.setdefault(r, dict(before=0, after=0, meas_leaf=0, parts=set()))
            d["parts"].add(p)
            for k in ("before", "after"):
                v = [cumf(n, E[k]) for n in ns]; d[k] = max(d[k], max(v) - min(v))
            v = [meas[n] for n in ns if n in meas]; d["meas_leaf"] = max(d["meas_leaf"], max(v) - min(v)) if v else d["meas_leaf"]
        v = sorted(reg.items(), key=lambda kv: -kv[1]["before"])
        P = lambda k, q: round(float(np.percentile([x[k] for _, x in v], q)), 1)
        out[nm] = dict(legs=len(ids), legs_rib_grouped=int(msk.sum()), coef_d0_k1_k2_kf=[round(float(x), 6) for x in c],
                       rms_before_all=round(float(np.sqrt((rb**2).mean())), 2), rms_before_rib=round(float(np.sqrt((rb[msk]**2).mean())), 2),
                       rms_after_all=round(float(np.sqrt((rc**2).mean())), 2), rms_after_rib=round(float(np.sqrt((rc[msk]**2).mean())), 2),
                       leg_meas_mean=round(float(X[:, 4].mean()), 2),
                       region_pair_before=dict(p50=P("before", 50), p90=P("before", 90), max=round(v[0][1]["before"], 1)),
                       region_pair_after=dict(p50=P("after", 50), p90=P("after", 90), max=round(max(x["after"] for _, x in v), 1)),
                       region_meas_leafspread=dict(p50=P("meas_leaf", 50), max=round(max(x["meas_leaf"] for _, x in v), 1)),
                       top=[(r, {k: (round(x[k], 1) if k != "parts" else sorted(x[k])[:4]) for k in x}) for r, x in v[:8]],
                       T060=[(r, {k: (round(x[k], 1) if k != "parts" else sorted(x[k])) for k in x}) for r, x in v if r == "T060"])
        print(C, nm, json.dumps({k: out[nm][k] for k in out[nm] if k not in ("top",)}))
        for r, x in out[nm]["top"]: print("   ", r, x)
    res[C] = out
json.dump(res, open(OUT, "w"), indent=1, default=str)
