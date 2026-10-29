"""CLK-MODEL-SWEEP-1 HEAD die tree (spine_fishbone inv2 r200): per node->parent leg fit vs routed GRT arrivals.
usage: fit_head_die.py G   (G has clk/tree.json, out_{TT,FF}/arr_*.txt)"""
import json, sys, collections
import numpy as np
G = sys.argv[1]
T = json.load(open(f"{G}/clk/tree.json"))
nodes = {int(k): v for k, v in T["nodes"].items()}
nb = {int(k): v for k, v in T["node_buf"].items()}
po, site = T["parent_of"], T["sites"]
ntap = collections.Counter(t["node"] for t in T["taps"])
S1 = (20.8281, 0.013984, 0.00033554)
man = lambda a, b: abs(a[0]-b[0]) + abs(a[1]-b[1])
out = {}
for C in ("TT", "FF"):
    arr = {p[1]: float(p[3]) for p in (l.split() for l in open(f"{G}/out_{C}/arr_{C}.txt")) if p[0] == "N"}
    rows, info = [], []
    for i, nd in nodes.items():
        if nd["parent"] is None: continue
        bi, bp = nb[i], nb[nd["parent"]]
        chain = [bi]; c = bi; ok = True
        while True:
            c = po.get(c)
            if c is None: ok = False; break
            chain.append(c)
            if c == bp: break
            if c.startswith("b") and not c.startswith("b0_r"): ok = False; break
        if not ok or bi not in arr or bp not in arr: continue
        pts = [tuple(site[x]) for x in reversed(chain)]
        segs = [man(a, b) for a, b in zip(pts, pts[1:])]
        n = len(segs)
        fo = len(nd["kids"]) + ntap.get(i, 0)
        meas = arr[bi] - arr[bp]
        old = sum(S1[0] + S1[1]*s + S1[2]*s*s for s in segs)
        rows.append([n, sum(segs), sum(s*s for s in segs), fo - 1, meas, old])
        info.append(dict(i=i, spine=bool(nd.get("spine")), rib=nd.get("rib"), L=sum(segs), level=nd["level"]))
    X = np.array(rows)
    c, *_ = np.linalg.lstsq(X[:, :4], X[:, 4], rcond=None)
    rc = X[:, 4] - X[:, :4] @ c; rm = X[:, 4] - X[:, 5]
    s = float(X[:, 4] @ X[:, 5] / (X[:, 5] @ X[:, 5])); rs = X[:, 4] - s*X[:, 5]
    rms = lambda v: round(float(np.sqrt((v**2).mean())), 2)
    # geometric "equal length = equal delay": per-unit-length rate (measured ps/um) spread -> residual vs mean-rate*L
    rate = X[:, 4].sum() / X[:, 1].sum(); rg = X[:, 4] - rate*X[:, 1]
    sp = np.array([d["spine"] for d in info])
    # spine DME balance check: rib-root arrivals (equal-length by construction)
    ribroots = sorted({nd.get("spine") and i for i, nd in nodes.items() if nd.get("spine") and not any(nodes[k].get("spine") for k in nd["kids"])} - {False, None, 0})
    rr = [arr[nb[i]] for i in ribroots if nb[i] in arr]
    out[C] = dict(legs=len(rows), spine_legs=int(sp.sum()), coef_d0_k1_k2_kf=[round(float(x), 6) for x in c],
                  rms_old_STAGE_1X=rms(rm), mean_old_err=round(float(rm.mean()), 2), uniform_scale=round(s, 3), rms_scaled=rms(rs),
                  rms_lengthonly=rms(rg), rate_ps_um=round(rate, 4), rms_fit=rms(rc),
                  rms_fit_spine=rms(rc[sp]), rms_old_spine=rms(rm[sp]), stages_total=int(X[:, 0].sum()),
                  ribroot_arr=dict(n=len(rr), min=round(min(rr), 1), max=round(max(rr), 1), spread=round(max(rr)-min(rr), 1)))
    print(C, json.dumps(out[C]))
json.dump(out, open(f"{G}/../fit_head_die_out.json" if len(sys.argv) < 3 else sys.argv[2], "w"), indent=1)
