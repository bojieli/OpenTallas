"""CLK-MODEL-SWEEP-1 generalisation of DIE-S81-17 cal_est.py: optional argv[6] = the --region-dme-stage-cal file the trial used (model column = that model incl. kf*(fanout-1)); FF model column uses the same (TT) model as the builder."""
"""DIE-S81-17 ESTIMATE: what intra-region skew is left if the region DME used a stage model calibrated on S81 go15
routed inv2 legs (DIE-QC-21 --region-dme-stage-cal form).  Per DME leg: measured (routed GRT, N rows) vs the go15 DME
model (STAGE_1X_TT BUFx24 fit) vs the fitted cal model (n*d0 + k1 L + k2 sum Ls^2 + kf*(fanout-1)).  A tap's tree
error below a node = sum of leg errors on its path; pair nominal skew error = difference of path sums below the LCA.
Reports per region: measured max nominal early skew between taps (|ea-eb| below LCA, all tap pairs in the same
partition) vs the residual if the model were the cal model (sum of cal residuals).  usage: TOOLS KIT ARR_PREFIX MAP OUT"""
import json, sys, math, collections
import numpy as np
sys.path.insert(0, sys.argv[1])
import die_trial as D
K, A, MP, OUT = sys.argv[2:6]
CAL = sys.argv[6] if len(sys.argv) > 6 and sys.argv[6] != "none" else None   # stage cal the trial USED (model column)
D.EVEN_LEGS = True
if CAL: D.load_stage_cal(CAL)
T = json.load(open(f"{K}/clock/tree.json"))
reg = json.load(open(MP))["part_region"]
nodes = {int(k): v for k, v in T["nodes"].items()}
nb = {int(k): v for k, v in T["node_buf"].items()}
ntap = collections.Counter(t["node"] for t in T["taps"])
res = {}
for C in ("TT", "FF"):
    arr = {p[1]: float(p[3]) for p in (l.split() for l in open(f"{A}_{C}/arr_{C}.txt")) if p[0] == "N"}   # early
    rows, ids = [], []
    for i, nd in nodes.items():
        if not nd.get("dme") or nd.get("parent") is None: continue
        p = nodes[nd["parent"]]
        pa, q = (p["x"], p["y"]), (nd["x"], nd["y"])
        if nd.get("snake"):
            pts = [pa] + [tuple(x) for x in nd["snake"]] + [q]
            segs = [D._man(a, b) for a, b in zip(pts, pts[1:])]; m = D.chain_ps(pts)
        else:
            pts = [tuple(x) for x in nd["route"]] if nd.get("route") else [pa, q]
            L = sum(D._man(a, b) for a, b in zip(pts, pts[1:]))
            n = max(1, math.ceil(L / 250.0 - 1e-9)); n += n % 2
            segs = [L / n] * n; m = D.leg_ps(L, 250.0)
        a, b = arr.get(nb[i]), arr.get(nb[nd["parent"]])
        if a is None or b is None: continue
        fo = len(nd["kids"]) + ntap.get(i, 0)
        rows.append([len(segs), sum(segs), sum(s * s for s in segs), fo - 1, a - b, m + D.DME_FANOUT_PS * (fo - 1)]); ids.append(i)
    X = np.array(rows, float)
    c, *_ = np.linalg.lstsq(X[:, :4], X[:, 4], rcond=None)
    rc = X[:, 4] - X[:, :4] @ c            # cal-model residual per leg
    rm = X[:, 4] - X[:, 5]                 # go15 model error per leg (measured - model)
    # model is scale-free for balance only if the error is proportional; also compute error after best uniform scale
    s = float(np.dot(X[:, 4], X[:, 5]) / np.dot(X[:, 5], X[:, 5]))
    rs = X[:, 4] - s * X[:, 5]
    E = {k: dict(zip(ids, v)) for k, v in (("cal", rc), ("model", rm), ("scaled", rs))}
    def pathsum(node, top, e):
        t = 0.0
        while node is not None and node != top:
            t += e.get(node, 0.0); node = nodes[node]["parent"]
        return t
    def anc(n):
        out = []
        while n is not None:
            out.append(n); n = nodes[n]["parent"]
        return out
    byp = collections.defaultdict(list)
    for t in T["taps"]:
        byp[t["part"]].append(t)
    reg_out = {}
    for part, ts in byp.items():
        best = dict(meas=0.0, cal=0.0, model=0.0, scaled=0.0)
        A_ = {t["port"]: anc(t["node"]) for t in ts}
        for i in range(len(ts)):
            for j in range(i + 1, len(ts)):
                ta, tb = ts[i], ts[j]
                sb = set(A_[tb["port"]])
                lca = next(x for x in A_[ta["port"]] if x in sb)
                if lca not in nb or nb[lca] not in arr: continue
                for k in ("cal", "model", "scaled"):
                    d = abs(pathsum(ta["node"], lca, E[k]) - pathsum(tb["node"], lca, E[k]))
                    best[k] = max(best[k], d)
        g = reg.get(part, part)
        r0 = reg_out.setdefault(g, dict(model=0.0, cal=0.0, scaled=0.0))
        for k in ("cal", "model", "scaled"):
            r0[k] = max(r0[k], best[k])
    v = sorted(reg_out.items(), key=lambda kv: -kv[1]["model"])
    q = lambda k, p: round(float(np.percentile([x[k] for _, x in v], p)), 1)
    res[C] = dict(coef=[round(float(x), 6) for x in c], rms_cal=round(float(np.sqrt((rc ** 2).mean())), 2),
                  rms_model=round(float(np.sqrt((rm ** 2).mean())), 2), uniform_scale=round(s, 3),
                  rms_scaled=round(float(np.sqrt((rs ** 2).mean())), 2), legs=len(ids),
                  region_max_pair_model_error=dict(p50=q("model", 50), p90=q("model", 90), max=round(v[0][1]["model"], 1)),
                  region_max_pair_residual_cal=dict(p50=q("cal", 50), p90=q("cal", 90), max=round(max(x["cal"] for _, x in v), 1)),
                  region_max_pair_residual_scaled=dict(p50=q("scaled", 50), p90=q("scaled", 90), max=round(max(x["scaled"] for _, x in v), 1)),
                  top=[(g, {k: round(x[k], 1) for k in x}) for g, x in v[:12]])
    print(C, json.dumps({k: res[C][k] for k in res[C] if k != "top"}))
    for g, x in res[C]["top"]:
        print("  ", g, x)
json.dump(res, open(OUT, "w"), indent=1)
