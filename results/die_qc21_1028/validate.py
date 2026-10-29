"""DIE-QC-21: fit a calibrated inv2 stage model (d0 + k1 Ls + k2 Ls^2 per stage, + kf per extra fanout of the leg's end
node; tap leg a1 d + a2 d^2) on trial13b routed legs, then predict glue-minus-core per DME region and compare with routed.
usage: validate.py TOOLS TRIAL ARR_PREFIX PLAN PART_REGION OUT.json"""
import json, sys, math, statistics as st
from collections import defaultdict
import numpy as np
sys.path.insert(0, sys.argv[1])
import die_trial as D, schema as S
K, A, PL, PR, OUT = sys.argv[2:7]
D.EVEN_LEGS = True
P = S.Plan(json.load(open(PL)))
T = json.load(open(f"{K}/clock/tree.json"))
nodes = {int(k): v for k, v in T["nodes"].items()}
nb = {int(k): v for k, v in T["node_buf"].items()}
contracts = {(p, n): tp for p, pp in P.parts.items() for n, _, _, tp in S.core_taps(P, pp["type"])}
rep = 250.0
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

def segs_of(i):
    nd = nodes[i]; p = nodes[nd["parent"]]
    pa, q = (p["x"], p["y"]), (nd["x"], nd["y"])
    if nd.get("snake"):
        pts = [pa] + [tuple(x) for x in nd["snake"]] + [q]
        return [D._man(a, b) for a, b in zip(pts, pts[1:])]
    pts = [tuple(x) for x in nd["route"]] if nd.get("route") else [pa, q]
    L = sum(D._man(a, b) for a, b in zip(pts, pts[1:]))
    n = max(1, math.ceil(L / rep - 1e-9)); n += n % 2
    return [L / n] * n

def feat(i):
    s = segs_of(i); fo = len(nodes[i]["kids"]) + ntap[i]
    return [len(s), sum(s), sum(x * x for x in s), fo - 1]

legs = [i for i, nd in nodes.items() if nd.get("dme") and nd.get("parent") is not None and nb.get(i) in arr["TT"]
        and nb.get(nd["parent"]) in arr["TT"]]
X = np.array([feat(i) for i in legs])
coef = {}
for C in ("TT", "FF"):
    y = np.array([arr[C][nb[i]] - arr[C][nb[nodes[i]["parent"]]] for i in legs])
    c, *_ = np.linalg.lstsq(X, y, rcond=None); coef[C] = c
# tap legs
tx, ty = [], {"TT": [], "FF": []}
for t in T["taps"]:
    n = t["node"]
    if not nodes[n].get("dme"): continue
    d = D._man((nodes[n]["x"], nodes[n]["y"]), tuple(t["xy"]))
    tx.append([1.0, d, d * d])
    for C in ("TT", "FF"): ty[C].append(arr[C]["port:" + t["port"]] - arr[C][nb[n]])
tx = np.array(tx); tc = {}
for C in ("TT", "FF"):
    c, *_ = np.linalg.lstsq(tx, np.array(ty[C]), rcond=None); tc[C] = c
print("leg coef TT", np.round(coef["TT"], 6), "FF", np.round(coef["FF"], 6))
print("tap coef TT", np.round(tc["TT"], 6), "FF", np.round(tc["FF"], 6))

def droot(i):
    rn = nodes[i].get("dme")
    while nodes[i].get("parent") is not None and nodes[nodes[i]["parent"]].get("dme") == rn:
        i = nodes[i]["parent"]
    return i
rows = defaultdict(lambda: dict(core=[], glue=[]))
for t in T["taps"]:
    n = t["node"]; rn = nodes[n].get("dme")
    if not rn: continue
    r0 = droot(n); i = n; pr = {"TT": 0.0, "FF": 0.0}
    d = D._man((nodes[n]["x"], nodes[n]["y"]), tuple(t["xy"]))
    for C in pr: pr[C] = float(tc[C] @ [1.0, d, d * d])
    while i != r0:
        f = np.array(feat(i))
        for C in pr: pr[C] += float(coef[C] @ f)
        i = nodes[i]["parent"]
    tp = contracts.get((t["part"], t["tap"]))
    rec = {f"pred_{C}": pr[C] for C in pr}
    for C in pr:
        rec[f"leafres_{C}"] = (arr[C][nb[n]] - arr[C][nb[r0]]) - (pr[C] - float(tc[C] @ [1.0, d, d * d]))
        rec[f"tapres_{C}"] = (arr[C]["port:" + t["port"]] - arr[C][nb[n]]) - float(tc[C] @ [1.0, d, d * d])
    for C in pr: rec[C] = arr[C]["port:" + t["port"]] - arr[C][nb[r0]]
    rows[rn]["core" if tp else "glue"].append(rec)
res = {}
for rn, dd in rows.items():
    if not dd["core"] or not dd["glue"]: continue
    m = lambda L, k: st.mean(x[k] for x in L)
    res[rn] = {f"{w}_{C}": round(m(dd["glue"], f"{w}_{C}" if w == "pred" else C) - m(dd["core"], f"{w}_{C}" if w == "pred" else C), 2)
               for w in ("pred", "routed") for C in ("TT", "FF")}
    for C in ("TT", "FF"):
        g = dd["glue"]
        res[rn][f"glue_spread_routed_{C}"] = round(max(x[C] for x in g) - min(x[C] for x in g), 1)
        res[rn][f"glue_spread_pred_{C}"] = round(max(x[f"pred_{C}"] for x in g) - min(x[f"pred_{C}"] for x in g), 1)
        res[rn][f"glue_spread_resid_{C}"] = round(max(x[C] - x[f"pred_{C}"] for x in g) - min(x[C] - x[f"pred_{C}"] for x in g), 1)
        res[rn][f"leafres_spread_{C}"] = round(max(x[f"leafres_{C}"] for x in g) - min(x[f"leafres_{C}"] for x in g), 1)
        res[rn][f"tapres_spread_{C}"] = round(max(x[f"tapres_{C}"] for x in g) - min(x[f"tapres_{C}"] for x in g), 1)
        allr = dd["core"] + dd["glue"]
        res[rn][f"abs_err_{C}"] = round(st.mean(abs(x[f"pred_{C}"] - x[C]) for x in allr), 2)
summ = {}
for k in ("c_", "su_c"):
    L = [v for n, v in res.items() if (n.startswith("c_") if k == "c_" else "su_c" in n)]
    s = {"regions": len(L)}
    for C in ("TT", "FF"):
        e = [v[f"pred_{C}"] - v[f"routed_{C}"] for v in L]
        s[C] = dict(pred_glue_minus_core_med=round(st.median(v[f"pred_{C}"] for v in L), 1),
                    routed_glue_minus_core_med=round(st.median(v[f"routed_{C}"] for v in L), 1),
                    err_min=round(min(e), 1), err_med=round(st.median(e), 1), err_max=round(max(e), 1),
                    glue_spread_routed_med_max=(st.median(v[f"glue_spread_routed_{C}"] for v in L), max(v[f"glue_spread_routed_{C}"] for v in L)),
                    glue_spread_pred_med_max=(st.median(v[f"glue_spread_pred_{C}"] for v in L), max(v[f"glue_spread_pred_{C}"] for v in L)),
                    glue_spread_resid_med_max=(st.median(v[f"glue_spread_resid_{C}"] for v in L), max(v[f"glue_spread_resid_{C}"] for v in L)),
                    leafres_spread_med_max=(st.median(v[f"leafres_spread_{C}"] for v in L), max(v[f"leafres_spread_{C}"] for v in L)),
                    tapres_spread_med_max=(st.median(v[f"tapres_spread_{C}"] for v in L), max(v[f"tapres_spread_{C}"] for v in L)),
                    tap_abs_err_med=round(st.median(v[f"abs_err_{C}"] for v in L), 2))
    summ[k] = s
json.dump(dict(leg_coef={C: [float(x) for x in coef[C]] for C in coef}, tap_coef={C: [float(x) for x in tc[C]] for C in tc},
               summary=summ, regions=res), open(OUT, "w"), indent=0)
print(json.dumps(summ, indent=1))
