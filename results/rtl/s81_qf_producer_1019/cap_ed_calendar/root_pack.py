#!/usr/bin/env python3
"""LEAD2-S81/TOK 10-19: EXACT (uncapped) global CAP-root packing over a generated per-frame calendar pool.
Six frames [h10 L01, h9 L02, h9 L03(+7), h10 R01, h9 R02, h9 R03(+7)] each pick one LOCALLY LEGAL calendar from
the pool of its topology; the CAP root carries one word per edge and adjacent-frame rows never merge, so the
union of all frames' frame-exit edges must be pairwise disjoint.  Complete DFS (MRV + forward check +
free-edge counting bound + W/E peer symmetry break); no word-count cap.  Result: a legal global calendar or a
proof that THIS pool has none (pool completeness is a separate question)."""
import gzip, json, sys, time
pool_path, out_path = sys.argv[1], sys.argv[2]
r = json.load(gzip.open(pool_path))
KIND = json.loads(sys.argv[3]) if len(sys.argv) > 3 else [(0, 0), (1, 0), (1, 7), (0, 0), (1, 0), (1, 7)]
pools = []
for kind, shift in KIND:
    seen = {}
    for c in r[kind]['candidates']:
        e = [w[0] + shift for w in c['ret']]
        if len(set(e)) != len(e):
            continue
        m = 0
        for t in e:
            m |= 1 << (t - 1700)
        seen.setdefault(m, dict(mask=m, n=len(e), edges=e, assign=c['assign'], ret=c['ret']))
    pools.append(sorted(seen.values(), key=lambda c: (c['n'], c['edges'])))
print('pools', [len(p) for p in pools], flush=True)
nodes = 0; t0 = time.time()
PEER = {3: 0, 4: 1, 5: 2} if len(KIND) == 6 else {}
def solve(dom, occ, chosen):
    global nodes
    nodes += 1
    if not dom:
        return chosen
    free = bin(((1 << 200) - 1) & ~occ).count('1')
    if sum(min(c['n'] for c in d) for d in dom.values()) > free:
        return None
    i = min(dom, key=lambda j: len(dom[j]))
    for c in dom[i]:
        nd = {}
        ok = True
        for j, d in dom.items():
            if j == i:
                continue
            v = [x for x in d if not (x['mask'] & c['mask'])]
            if j in PEER and PEER[j] == i:      # symmetry: peer index > chosen index of its twin
                v = [x for x in v if (x['n'], x['edges']) > (c['n'], c['edges'])]
            if i in PEER and PEER[i] == j:
                v = [x for x in v if (x['n'], x['edges']) < (c['n'], c['edges'])]
            if not v:
                ok = False; break
            nd[j] = v
        if not ok:
            continue
        s = solve(nd, occ | c['mask'], dict(chosen, **{str(i): c}))
        if s:
            return s
    return None
sol = solve({i: p for i, p in enumerate(pools)}, 0, {})
res = dict(pool=pool_path, pool_sizes=[len(p) for p in pools], nodes=nodes, seconds=time.time() - t0,
           complete_search=True, word_cap=None, solution=sol,
           words=None if not sol else sum(c['n'] for c in sol.values()),
           edges=None if not sol else sorted(t for c in sol.values() for t in c['edges']))
json.dump(res, open(out_path, 'w'), indent=1)
print('ROOT_PACK', 'FOUND' if sol else 'NONE', 'nodes', nodes, 'sec', round(time.time() - t0, 1), flush=True)
