"""Planning probe: complete-coverage related-pair bound per clock region WITH per-tap die-level trim (added delay
x_p in [0, XMAX], early side adds MIN_RATIO*x: the trim's own uncredited early/late range), CPPR credit only at the
region's H-tree node (mesh NOT common).  Both directions (setup and hold) per pair.  Not gate evidence."""
import sys, json, re, collections, itertools
import numpy as np, scipy.sparse as sp
from scipy.optimize import linprog
D, PLAN, TOOLS, OUT = sys.argv[1:5]
XMAX = float(sys.argv[5]) if len(sys.argv) > 5 else 150.0
RATIO = 0.97
sys.path.insert(0, TOOLS)
import schema as S
P = S.Plan(S.load(PLAN)); M = json.load(open(f"{D}/mesh.json"))
reg = {t["port"]: t["region"] for t in M["taps"]}; part = {t["port"]: t["part"] for t in M["taps"]}
tb = collections.defaultdict(list)
for t in M["taps"]: tb[t["part"]].append(t["port"])
rtag = {g["k"]: g["tag"] for g in M["meta"]["regions"]}
conn = {tuple(sorted((p["src"]["part"], p["dst"]["part"]))) for p in P.ports.values()
        if p["src"]["part"] in tb and p["dst"]["part"] in tb and p["src"]["part"] != p["dst"]["part"]}
pairs = set()
for ts in tb.values(): pairs.update(itertools.combinations(sorted(ts), 2))
landed = 0
for u, v in conn:
    if reg[tb[u][0]] != reg[tb[v][0]]: landed += 1; continue
    pairs.update((a, b) for a in tb[u] for b in tb[v])
pairs = sorted(pairs)
res = dict(pairs=len(pairs), landed_part_pairs=len([1 for u, v in conn if reg[tb[u][0]] != reg[tb[v][0]]]), xmax_ps=XMAX)
for corner in ("TT", "FF"):
    N = {}
    for l in open(f"{D}/tree_{corner}.txt"):
        f = l.split()
        if len(f) >= 4: N[f[1]] = (float(f[2]), float(f[3]))
    cred = {}
    for k, tg in rtag.items():
        nm = [n for n in N if re.match(rf"ckm_n\d+_{tg}$", n)]
        cred[k] = (N[nm[0]][0] - N[nm[0]][1]) if nm else 0.0
    arr = {}
    for l in open(f"{D}/taps_{corner}.txt"):
        f = l.split(); arr[f[1]] = (float(f[2]), float(f[3]))
    res[corner] = dict(region_credit_ps={rtag[k]: round(v, 1) for k, v in cred.items()})
    ports = sorted(arr); idx = {p: i for i, p in enumerate(ports)}; n = len(ports)
    def dmg0(a, b):
        c = min(cred[reg[a]], arr[a][0]-arr[a][1], arr[b][0]-arr[b][1])
        return max(arr[a][0]-arr[b][1], arr[b][0]-arr[a][1]) - c
    res[corner]["no_trim_bound_ps"] = round(max(dmg0(a, b) for a, b in pairs), 2)
    res[corner]["floor_uncredited_ps"] = round(max((arr[a][0]-arr[a][1]+arr[b][0]-arr[b][1])/2 - cred[reg[a]] for a, b in pairs), 2)
    out = res[corner]
    out["corner_alone"] = None
    res[corner]["_arr"] = arr; res[corner]["_cred"] = cred
# joint LP: one physical trim per tap must serve both corners -> x_TT, x_FF tied by measured ratio FF/TT ~ k
rows, cols, vals, rhs = [], [], [], []
ports = sorted(res["TT"]["_arr"]); idx = {p: i for i, p in enumerate(ports)}; n = len(ports)
KFF = 0.80   # BUF chain FF/TT delay ratio (ASAP7 BUFx stock chains, clock_phase_lp hull ~0.78-0.82)
g = n
def add(co, b):
    k = len(rhs)
    for i, v in co.items(): rows.append(k); cols.append(i); vals.append(v)
    rhs.append(b)
for corner, kc in (("TT", 1.0), ("FF", KFF)):
    arr, cred = res[corner]["_arr"], res[corner]["_cred"]
    for a, b in pairs:
        for p, q in ((a, b), (b, a)):
            c = min(cred[reg[p]], arr[p][0]-arr[p][1], arr[q][0]-arr[q][1])
            fixed = arr[p][0] - arr[q][1] - c
            # (L_p + kc x_p) - (E_q + RATIO kc x_q) - c <= gamma ; trim range is NOT credited (below region node)
            add({idx[p]: kc, idx[q]: -RATIO*kc, g: -1.0}, -fixed)
A = sp.csr_matrix((vals, (rows, cols)), shape=(len(rhs), n+1))
cost = np.full(n+1, 1e-6); cost[g] = 1.0
r = linprog(cost, A_ub=A, b_ub=np.array(rhs), bounds=[(0, XMAX)]*n + [(0, None)], method="highs")
res["joint_lp"] = dict(success=bool(r.success), message=r.message)
if r.success:
    x = r.x[:n]; res["joint_lp"].update(bound_ps=round(float(r.x[g]), 2), trimmed_taps=int((x > 0.5).sum()), max_trim_ps=round(float(x.max()), 1))
    for corner, kc in (("TT", 1.0), ("FF", KFF)):
        arr, cred = res[corner]["_arr"], res[corner]["_cred"]
        def dm(a, b):
            c = min(cred[reg[a]], arr[a][0]-arr[a][1], arr[b][0]-arr[b][1])
            La, Ea = arr[a][0]+kc*x[idx[a]], arr[a][1]+RATIO*kc*x[idx[a]]
            Lb, Eb = arr[b][0]+kc*x[idx[b]], arr[b][1]+RATIO*kc*x[idx[b]]
            return max(La-Eb, Lb-Ea) - c
        w = max((dm(a, b), a, b) for a, b in pairs)
        res["joint_lp"][corner] = [round(w[0], 2), w[1], w[2]]
for c in ("TT", "FF"): res[c].pop("_arr"); res[c].pop("_cred")
json.dump(res, open(OUT, "w"), indent=1); print(json.dumps(res, indent=1))
