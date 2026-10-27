#!/usr/bin/env python3
"""PATH-HBM-R12: price hub-internal core-core (cc) leg growth t_banks -> planA2 on top of b1_lane_traversal.
delta per cc conn = max over candidate copies (len(regs_um) + serial_k-1) - baseline len(regs_um).
per op: lower = max delta over cc conns touching the op families (one hub cc leg per record, static pad to longest);
upper = longest directed module-pair path (sum) within those families."""
import json, sys, re, collections, importlib.util
W, base, cand, lane_price, out = sys.argv[1:6]
spec = importlib.util.spec_from_file_location('T', W + '/tools/hbm_b2/b1_lane_traversal.py'); T = importlib.util.module_from_spec(spec)
sys.argv = ['x']; spec.loader.exec_module(T)
def load(p):
    P = json.load(open(p + '/die_plan.json')); r = {}
    for tn in ('q_hub_nw', 'q_hub_ne'):
        d = {}
        for s in P['partition_types'][tn]['internal_stations']:
            if 'bus:' in str(s.get('conn')): continue
            c = len(s['regs_um']) + max(int(s.get('serial_k') or 1) - 1, 0)
            d[s['conn']] = max(d.get(s['conn'], 0), c)
        r[tn] = d
    return r
B, C = load(base), load(cand)
def inst(x): return x.split('.')[0]
def fam(x):
    i = re.sub(r'__q\d+$', '', inst(x)); return T.family(i)
res = dict(per_hub={}, ops={})
edges = collections.defaultdict(dict)  # fam -> {(a,b): delta}
allrows = []
for tn in B:
    new = set(C[tn]) - set(B[tn]); gone = set(B[tn]) - set(C[tn])
    ds = []
    for conn, c in C[tn].items():
        if conn not in B[tn]: continue
        l, cap = conn.split('|')
        d = c - B[tn][conn]; ds.append(d)
        fs = {fam(l), fam(cap)}
        a = re.sub(r'(_Q\d*|__q\d+)$', '', inst(l)); b = re.sub(r'(_Q\d*|__q\d+)$', '', inst(cap))
        allrows.append((tn, conn, d, sorted(fs)))
        for f in fs:
            edges[f][(a, b)] = max(edges[f].get((a, b), -99), d)
    h = collections.Counter(ds)
    res['per_hub'][tn] = dict(matched=len(ds), new_conns=len(new), gone_conns=len(gone), delta_hist=dict(sorted(h.items())),
                              max=max(ds), sum_pos=sum(x for x in ds if x > 0))
def longest(E):
    g = collections.defaultdict(list)
    for (a, b), d in E.items():
        if a != b and d > 0: g[a].append((b, d))
    memo = {}
    def go(n, seen):
        best = 0
        for m, d in g.get(n, ()):
            if m in seen: continue
            best = max(best, d + go(m, seen | {m}))
        return best
    return max([go(n, {n}) for n in list(g)] or [0])
for op, fs in T.OP_FAMILIES:
    lo = max([max([d for d in edges[f].values()] or [0]) for f in fs] + [0])
    up = max([longest(edges[f]) for f in fs] + [0])
    res['ops'][op] = dict(families=fs, lower=lo, upper=up)
json.dump(res, open(out, 'w'), indent=1)
print(json.dumps(res['per_hub'])); print(json.dumps(res['ops']))
top = sorted(allrows, key=lambda r: -r[2])[:12]
for r in top: print(r)
