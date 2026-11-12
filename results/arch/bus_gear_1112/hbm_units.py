import sys, json, collections
sys.path[:0] = ['tools', 'tools/throughput', 'tools/token_pass']
import importlib.util
spec = importlib.util.spec_from_file_location('p', 'tools/token_pass/hbm_price_d44t.py')
src = open('tools/token_pass/hbm_price_d44t.py').read().split('json.dump(out')[0]
g = {'__name__': 'p'}
exec(compile(src, 'p', 'exec'), g)
run, recs, T, DT, cf = g['run'], g['recs'], g['T'], g['DT'], g['cf']
A1 = g['A1']
ref = run(extra=dict(SU=3, **A1['extra']), south='exact', sfu=A1['sfu'], tnode=True)
print('ref', ref, 1.2e12/833/ref*0+ (1e12/833.0)/ref)
print('units', collections.Counter(r.unit for r in recs))
for u in ['IDX', 'SM', 'SU', 'COLL', 'FUSED', 'HBM', 'LOAD', 'VM']:
    e = dict(SU=3, **A1['extra']); e[u] = e.get(u, 0) + 1
    t = run(extra=e, south='exact', sfu=A1['sfu'], tnode=True)
    print('dT/d(+1 per', u, 'record) =', round(t - ref, 2))
# stretch: per-unit cost x2 (2:1 gearbox on that unit's streaming bus, bound)
def stretch(unit, f):
    def gfn(r, dyn, L):
        c = cf(r, dyn, L); t = c[0]
        if r.unit == unit: t *= f
        return (t, c[1], c[2])
    return T.schedule(recs, DT.POS, 'S2', cost_fn=gfn)['total_cycles']
b0 = run(ab=False)
for u in ['IDX', 'SM', 'SU', 'COLL', 'FUSED']:
    print('stretch x2', u, round(stretch(u, 2) - b0, 1), 'of base', round(b0, 1))
