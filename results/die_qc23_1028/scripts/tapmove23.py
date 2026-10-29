"""DIE-QC-23: is the trial14 -> trial15/16 routed tap move designed (model-predicted) or tree instability?
Fixed calibrated model (val14 leg/tap coef, validate.py form) predicts root->tap for both trees; compare with routed.
usage: tapmove23.py TOOLS T14 ARR14 T16 ARR16 VAL14 OUT"""
import json, sys, math, statistics as st
from collections import defaultdict
import numpy as np
sys.path.insert(0, sys.argv[1]); import die_trial as D
K1, A1, K2, A2, V, OUT = sys.argv[2:8]
v = json.load(open(V)); coef = np.array(v["leg_coef"]["TT"]); tc = np.array(v["tap_coef"]["TT"])
def load(K, A):
    T = json.load(open(f"{K}/clock/tree.json")); N = {int(k): x for k, x in T["nodes"].items()}
    nb = {int(k): x for k, x in T["node_buf"].items()}; nt = defaultdict(int)
    for t in T["taps"]: nt[t["node"]] += 1
    a = {}
    for l in open(f"{A}_TT/arr_TT.txt"):
        p = l.split()
        if p[0] == "N": a[p[1]] = float(p[2])
        elif p[0] == "T": a["port:" + p[1]] = float(p[2])
    def segs(i):
        nd = N[i]; p = N[nd["parent"]]; pa, q = (p["x"], p["y"]), (nd["x"], nd["y"])
        if nd.get("snake"):
            pts = [pa] + [tuple(x) for x in nd["snake"]] + [q]; return [D._man(x, y) for x, y in zip(pts, pts[1:])]
        pts = [tuple(x) for x in nd["route"]] if nd.get("route") else [pa, q]
        L = sum(D._man(x, y) for x, y in zip(pts, pts[1:])); n = max(1, math.ceil(L / 250 - 1e-9)); n += n % 2
        return [L / n] * n
    out = {}
    for t in T["taps"]:
        n = t["node"]; rn = N[n].get("dme")
        if not rn: continue
        i = n; r0 = n
        while N[r0].get("parent") is not None and N[N[r0]["parent"]].get("dme") == rn: r0 = N[r0]["parent"]
        d = D._man((N[n]["x"], N[n]["y"]), tuple(t["xy"])); pr = float(tc @ [1, d, d * d]); leaf = d; stg = 0
        while i != r0:
            s = segs(i); pr += float(coef @ [len(s), sum(s), sum(x * x for x in s), len(N[i]["kids"]) + nt[i] - 1]); stg += len(s); i = N[i]["parent"]
        out[t["port"]] = dict(rn=rn, pred=pr, routed=a["port:" + t["port"]] - a[nb[r0]], root=a[nb[r0]], leaf_um=leaf, stages=stg)
    return out
a, b = load(K1, A1), load(K2, A2)
rows = []
for p in a:
    if p not in b: continue
    rows.append(dict(port=p, rn=a[p]["rn"], d_routed_abs=(b[p]["routed"] + b[p]["root"]) - (a[p]["routed"] + a[p]["root"]),
                     d_root=b[p]["root"] - a[p]["root"], d_pred=b[p]["pred"] - a[p]["pred"], d_rt=b[p]["routed"] - a[p]["routed"],
                     res14=a[p]["routed"] - a[p]["pred"], res16=b[p]["routed"] - b[p]["pred"], leaf14=a[p]["leaf_um"], leaf16=b[p]["leaf_um"]))
for r in rows: r["unexplained"] = r["d_rt"] - r["d_pred"]
ab = lambda k: sorted(abs(r[k]) for r in rows)
S = {k: dict(max=round(ab(k)[-1], 1), p99=round(ab(k)[int(.99 * len(rows))], 1), over30=sum(x > 30 for x in ab(k)))
     for k in ("d_routed_abs", "d_root", "d_pred", "d_rt", "unexplained", "res14", "res16")}
w = max(rows, key=lambda r: abs(r["d_routed_abs"])); S["worst"] = {k: (round(x, 1) if isinstance(x, float) else x) for k, x in w.items()}
lu = [r for r in rows if abs(r["unexplained"]) > 30]
S["unexplained_gt30_leaf16_med"] = round(st.median(r["leaf16"] for r in lu), 1) if lu else None
S["unexplained_gt30_regions"] = len({r["rn"] for r in lu})
S["leaf_over_400_t14_t16"] = (sum(r["leaf14"] > 400 for r in rows), sum(r["leaf16"] > 400 for r in rows))
S["taps"] = len(rows)
json.dump(dict(summary=S, rows=rows), open(OUT, "w")); print(json.dumps(S, indent=1))
