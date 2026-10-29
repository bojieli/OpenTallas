"""CLK-MODEL-SWEEP-1 / KV: per-leg model vs routed on the DIE-KV-14/15 fishbone-feed link_htree inverter tree (die_trial kit
--tree-form link_htree --feed feed_fishbone.json --clock-cell inv --rep-um 150, balance_legalize = geometric zero-skew).
Legs = node b<i> -> parent node b<p> through the r<i>_k repeaters (one cell = one stage), from tree.json sites/parent_of.
Measured leg = arr_rise(Y child) - arr_rise(Y parent) from routed GRT arr_<C>.txt N rows (col 2 late / col 3 early).
BEFORE (builder = geometry only): (a) delay ~ k*L (equal length = equal delay; best single k), (b) k*L + c (per-leg const).
AFTER: n*d0 + k1 L + k2 sum Ls^2 + kf (fanout-1).  Also tap legs (leaf driver Y -> tap port) included as wire-only
residual (measured, unchanged by stage cal).  Per region (tap's nearest region_root ancestor): measured max in-region tap
spread vs max |pathsum_a - pathsum_b| below LCA of the leg residuals for each model.  usage: cal_est_kv.py DIR"""
import json, sys, collections, math
import numpy as np
Dd = sys.argv[1]
T = json.load(open(f"{Dd}/tree.json"))
nodes = {int(k): v for k, v in T["nodes"].items()}
nb = {int(k): v for k, v in T["node_buf"].items()}
site, par = T["sites"], T["parent_of"]
ntap = collections.Counter(t["node"] for t in T["taps"])
md = lambda a, b: abs(a[0] - b[0]) + abs(a[1] - b[1])
# region of every node: nearest ancestor-or-self with region_root; in-region = not a feed node (feed nodes belong to links)
def region_of(i):
    while i is not None:
        if nodes[i].get("region_root") is not None:
            return nodes[i]["region_root"], i
        i = nodes[i]["parent"]
    return None, None
out = {}
for C in ("TT", "FF"):
    rows = [l.split() for l in open(f"{Dd}/arr_{C}.txt")]
    arr = {p[1]: float(p[2]) for p in rows if p[0] == "N"}
    tarr = {p[1]: float(p[2]) for p in rows if p[0] == "T"}
    legs, ids, kinds = [], [], []
    for i, nd in nodes.items():
        if nd["parent"] is None:
            continue
        cb, pb = nb[i], nb[nd["parent"]]
        chain = [cb]
        while chain[-1] != pb:
            chain.append(par[chain[-1]])
        chain = chain[::-1]                  # pb .. cb
        segs = [md(site[a], site[b]) for a, b in zip(chain, chain[1:])]
        if cb not in arr or pb not in arr:
            continue
        fo = len(nd["kids"]) + ntap.get(i, 0)
        legs.append([len(segs), sum(segs), sum(s * s for s in segs), fo - 1, arr[cb] - arr[pb]])
        ids.append(i); kinds.append("feed" if nd.get("feed") else "region")
    X = np.array(legs, float)
    y = X[:, 4]
    reg_mask = np.array([k == "region" for k in kinds])
    def fit(cols, mask):
        c, *_ = np.linalg.lstsq(X[mask][:, cols], y[mask], rcond=None)
        r = y - X[:, cols] @ c
        return c, r
    # fit on region legs (the balanced part); report rms on region legs
    kL = float(np.dot(X[reg_mask, 1], y[reg_mask]) / np.dot(X[reg_mask, 1], X[reg_mask, 1]))
    r_kL = y - kL * X[:, 1]
    A1 = np.c_[X[:, 1], np.ones(len(X))]
    c_lin, *_ = np.linalg.lstsq(A1[reg_mask], y[reg_mask], rcond=None)
    r_lin = y - A1 @ c_lin
    c_cal, r_cal = fit([0, 1, 2, 3], reg_mask)
    rms = lambda r: round(float(np.sqrt((r[reg_mask] ** 2).mean())), 2)
    # rms of leg delay around per-(level) mean of region legs (the "equal-geometry group" spread, crude)
    lvl = collections.defaultdict(list)
    for j, i in enumerate(ids):
        if kinds[j] == "region":
            lvl[nodes[i]["level"]].append(y[j])
    grp = np.concatenate([np.array(v) - np.mean(v) for v in lvl.values()])
    E = {k: dict(zip(ids, v)) for k, v in (("kL", r_kL), ("lin", r_lin), ("cal", r_cal))}
    # per-merge-node measured imbalance: mean tap arrival via each kid (taps under the kid), 2-kid region nodes
    kids_taps = collections.defaultdict(list)
    tap_reg = {}
    for t in T["taps"]:
        a = t["node"]
        rg, rr = region_of(a)
        tap_reg[t["port"]] = (rg, rr)
        while a is not None:
            kids_taps[a].append(t["port"])
            a = nodes[a]["parent"]
    def anc(n):
        o = []
        while n is not None:
            o.append(n); n = nodes[n]["parent"]
        return o
    def pathsum(n, top, e):
        s = 0.0
        while n is not None and n != top:
            s += e.get(n, 0.0); n = nodes[n]["parent"]
        return s
    byreg = collections.defaultdict(list)
    for t in T["taps"]:
        byreg[tap_reg[t["port"]][0]].append(t)
    R = {}
    for rg, ts in byreg.items():
        if rg is None:
            continue
        A_ = {t["port"]: anc(t["node"]) for t in ts}
        best = dict(meas=0.0, kL=0.0, lin=0.0, cal=0.0, leaf_wire=0.0)
        # leaf wire leg (driver Y -> tap): measured, same in every model
        # leaf: measured driver-node Y -> tap = pads (designed, measured) + parity inverter q (one stage the geometric
        # builder does not see; the cal model prices it as d0) + wire.  lwm[k] = residual of that leaf per model.
        lw = {t["port"]: tarr[t["port"]] - arr[nb[t["node"]]] for t in ts}
        qd = {t["port"]: (arr["q" + nb[t["node"]][1:] + "_" + t["port"]] - arr[par["q" + nb[t["node"]][1:] + "_" + t["port"]]])
              if ("q" + nb[t["node"]][1:] + "_" + t["port"]) in arr else None for t in ts}
        pd_ = {}
        for t in ts:
            pp = [x for x in t["path"] if x.startswith("p")]
            pd_[t["port"]] = (arr[pp[-1]] - arr[nb[t["node"]]]) if pp else 0.0
        lw = {p: lw[p] - pd_[p] for p in lw}   # model columns: designed pads dropped (a calibrated balancer needs none)
        lwm = {"kL": lw, "lin": lw,
               "cal": {p: lw[p] - (c_cal[0] if qd[p] is not None else 0.0) for p in lw}}
        best["meas"] = max(tarr[t["port"]] for t in ts) - min(tarr[t["port"]] for t in ts)
        best["leaf_wire"] = max(lw.values()) - min(lw.values())
        best["nq"] = sum(1 for p in qd if qd[p] is not None)
        pads = sum(1 for t in ts if any(p.startswith("p") for p in t["path"]))
        for a in range(len(ts)):
            for b in range(a + 1, len(ts)):
                ta, tb = ts[a], ts[b]
                sb = set(A_[tb["port"]])
                lca = next(x for x in A_[ta["port"]] if x in sb)
                for k in ("kL", "lin", "cal"):
                    d = abs(pathsum(ta["node"], lca, E[k]) + lwm[k][ta["port"]] - pathsum(tb["node"], lca, E[k]) - lwm[k][tb["port"]])
                    best[k] = max(best[k], d)
        best["ntaps"] = len(ts); best["pads"] = pads
        R[rg] = best
    v = sorted(R.items(), key=lambda kv: -kv[1]["meas"])
    nopad = [x for _, x in v if x["pads"] == 0]
    q = lambda arrx, k, p: round(float(np.percentile([x[k] for x in arrx], p)), 1)
    res = dict(legs=int(len(ids)), region_legs=int(reg_mask.sum()), feed_legs=int((~reg_mask).sum()),
               coef_cal=[round(float(x), 6) for x in c_cal], k_L=round(kL, 5), lin=[round(float(x), 5) for x in c_lin],
               rms_kL=rms(r_kL), rms_lin=rms(r_lin), rms_cal=rms(r_cal),
               rms_around_level_mean=round(float(np.sqrt((grp ** 2).mean())), 2),
               feed_rms_cal_with_region_fit=round(float(np.sqrt((r_cal[~reg_mask] ** 2).mean())), 2),
               leg_ps_mean=round(float(y[reg_mask].mean()), 2), stages_mean=round(float(X[reg_mask, 0].mean()), 2),
               regions=len(R))
    for k in ("meas", "kL", "lin", "cal", "leaf_wire"):
        res[f"region_{k}"] = dict(p50=q(v and [x for _, x in v], k, 50), p90=q([x for _, x in v], k, 90),
                                  max=round(max(x[k] for _, x in v), 1),
                                  max_nopad=round(max(x[k] for x in nopad), 1))
    res["top"] = [(g, {k: round(x[k], 1) for k in x}) for g, x in v[:10]]
    out[C] = res
    print(C, json.dumps({k: res[k] for k in res if k != "top"}))
    for g, x in res["top"]:
        print("  ", g, x)
json.dump(out, open(f"{Dd}/cal_est_kv.json", "w"), indent=1)
