"""PATH-S81-PD12: per-pair U (pd10 pairu gate formula, routed gap term optional) on neighbour mesh-load pairs <= 1 mm,
all pairs and the H-tree L1/L2 split-line pairs (loads on opposite sides of x = root x or y = root y).
usage: pairs.py MC.json PLACE.json REC.json [ROUTED_MESH.json|-]   prints one JSON line"""
import json, math, sys
mc, place, recp = sys.argv[1:4]; rtp = sys.argv[4] if len(sys.argv) > 4 else "-"
S = json.load(open(mc)); P = json.load(open(place)); rec = json.load(open(recp))
rx, ry = rec["root_xy"]
L = S["loads"]; arr = S["arr"]; gv = S["grad_vec_ps"]; ns = len(arr)
rt = json.load(open(rtp))["stubs"] if rtp != "-" else {}
gap = [rt[k]["late"] - arr[0][i] if k in rt else 0.0 for i, k in enumerate(L)]
xy = {k: (P[k]["x"], P[k]["y"]) for k in L if k in P and not k.startswith("ckm_br_")}
idx = [i for i, k in enumerate(L) if k in xy]
R_ = 1000.0; cell = {}
for i in idx:
    x, y = xy[L[i]]; cell.setdefault((int(x // R_), int(y // R_)), []).append(i)
U, X, Y = [], [], []
for i in idx:
    x, y = xy[L[i]]
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            for j in cell.get((int(x // R_) + dx, int(y // R_) + dy), []):
                if j <= i: continue
                xj, yj = xy[L[j]]
                if abs(x - xj) + abs(y - yj) > R_: continue
                ds = [arr[s][i] - arr[s][j] for s in range(ns)]
                mcv = ds[1:]; mu = sum(mcv) / len(mcv); sd = (sum((v - mu) ** 2 for v in mcv) / max(1, len(mcv) - 1)) ** .5
                g = math.hypot(gv[i][0] - gv[j][0], gv[i][1] - gv[j][1]); gp = gap[i] - gap[j]
                u = max(max(abs(v + gp) for v in ds), abs(mu + gp) + 3 * sd) + g
                U.append(u)
                if (x - rx) * (xj - rx) < 0: X.append(u)
                if (y - ry) * (yj - ry) < 0: Y.append(u)
def q(v, p):
    v = sorted(v); return round(v[min(len(v) - 1, int(p * len(v)))], 1) if v else None
print(json.dumps(dict(mc=mc, pairs=len(U), p50=q(U, .5), p90=q(U, .9), p99=q(U, .99), max=q(U, 1), over80=sum(u > 80 for u in U),
                      xline=dict(n=len(X), p50=q(X, .5), max=q(X, 1)), yline=dict(n=len(Y), p50=q(Y, .5), max=q(Y, 1)),
                      nominal_skew=S["summary"].get("nominal_skew_ps"), mc_worst=S["summary"].get("mc_worst_skew_ps"),
                      sigma=S["summary"].get("per_load_sigma_ps"), gw=S["summary"].get("gradient_worst_pair_ps"))))
