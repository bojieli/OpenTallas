"""DIE-S81-18 bk_sel two-root ESTIMATE on go15 (UNCHECKED projection).  Per-leg cal residual (S81 inv2 stage cal) as in
DIE-S81-17 cal_est; bk_sel taps split in two halves (by the long axis median); per half: max |pathsum diff below LCA|
of the cal residual = the residual skew a calibrated DME leaves (same tree topology inside the half); plus leg-count /
wire-length statistics of the path below the region root -> the two-root form shortens each half's deepest path.
usage: TOOLS KIT ARR_PREFIX STAGECAL PART"""
import json, sys, math, collections
import numpy as np
sys.path.insert(0, sys.argv[1])
import die_trial as D
K, A, CALF, PART = sys.argv[2:6]
T = json.load(open(f"{K}/clock/tree.json"))
cal = json.load(open(CALF))
nodes = {int(k): v for k, v in T["nodes"].items()}
nb = {int(k): v for k, v in T["node_buf"].items()}
ntap = collections.Counter(t["node"] for t in T["taps"])
taps = [t for t in T["taps"] if t["part"] == PART]
out = {}
for C in ("TT", "FF"):
    coef = cal["leg"] if C == "TT" else cal["leg_FF"]
    arr = {p[1]: float(p[3]) for p in (l.split() for l in open(f"{A}_{C}/arr_{C}.txt")) if p[0] == "N"}
    res, L = {}, {}
    for i, nd in nodes.items():
        if not nd.get("dme") or nd.get("parent") is None:
            continue
        p = nodes[nd["parent"]]
        pa, q = (p["x"], p["y"]), (nd["x"], nd["y"])
        if nd.get("snake"):
            pts = [pa] + [tuple(x) for x in nd["snake"]] + [q]
            segs = [D._man(a, b) for a, b in zip(pts, pts[1:])]
        else:
            pts = [tuple(x) for x in nd["route"]] if nd.get("route") else [pa, q]
            Lg = sum(D._man(a, b) for a, b in zip(pts, pts[1:]))
            n = max(1, math.ceil(Lg / 250.0 - 1e-9)); n += n % 2
            segs = [Lg / n] * n
        a, b = arr.get(nb[i]), arr.get(nb[nd["parent"]])
        if a is None or b is None:
            continue
        fo = len(nd["kids"]) + ntap.get(i, 0)
        x = [len(segs), sum(segs), sum(s * s for s in segs), fo - 1]
        res[i] = (a - b) - sum(c * v for c, v in zip(coef, x))
        L[i] = sum(segs)

    def anc(n):
        o = []
        while n is not None:
            o.append(n); n = nodes[n]["parent"]
        return o

    def ps(n, top, e):
        t = 0.0
        while n is not None and n != top:
            t += e.get(n, 0.0); n = nodes[n]["parent"]
        return t
    xs = np.array([t["xy"][0] for t in taps]); ys = np.array([t["xy"][1] for t in taps])
    ax = 0 if np.ptp(xs) >= np.ptp(ys) else 1
    med = float(np.median(xs if ax == 0 else ys))
    half = {t["port"]: int((t["xy"][ax]) > med) for t in taps}
    A_ = {t["port"]: anc(t["node"]) for t in taps}

    def worst(sel):
        w, wl = 0.0, 0.0
        for i in range(len(sel)):
            for j in range(i + 1, len(sel)):
                ta, tb = sel[i], sel[j]
                sb = set(A_[tb["port"]])
                lca = next(x for x in A_[ta["port"]] if x in sb)
                d = abs(ps(ta["node"], lca, res) - ps(tb["node"], lca, res))
                w = max(w, d)
                wl = max(wl, ps(ta["node"], lca, L), ps(tb["node"], lca, L))
        return round(w, 1), round(wl, 1)
    allw = worst(taps)
    h0 = worst([t for t in taps if half[t["port"]] == 0]); h1 = worst([t for t in taps if half[t["port"]] == 1])
    out[C] = dict(taps=len(taps), span_um=[round(float(np.ptp(xs)), 1), round(float(np.ptp(ys)), 1)], cut_axis="xy"[ax],
                  cut_at_um=round(med, 1), one_root_resid_max_ps=allw[0], one_root_max_path_wire_um=allw[1],
                  half0=dict(n=sum(1 for v in half.values() if v == 0), resid_max_ps=h0[0], max_path_wire_um=h0[1]),
                  half1=dict(n=sum(1 for v in half.values() if v == 1), resid_max_ps=h1[0], max_path_wire_um=h1[1]))
    print(C, json.dumps(out[C]))
json.dump(out, open(f"bksel_est_{PART}.json", "w"), indent=1)
