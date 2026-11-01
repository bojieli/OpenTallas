"""DIE-S81-46: a3 die-clock feed from DIE-S81-42 feed_sb6.json -- re-parent the three a3 partitions on their new
abutments (taps on the shared edge, the feed tool's convention); every other edge unchanged.  usage: feed_a3.py IN PLAN OUT"""
import json, sys
sys.path.insert(0, sys.argv[4] + '/tools/die_plan')
import schema as S
f = json.load(open(sys.argv[1])); P = S.Plan(S.load(sys.argv[2]), sys.argv[2])
par, tap = f['parent'], f['tap']
def shared(a, b):
    ax0, ay0, ax1, ay1 = P.rect(a); bx0, by0, bx1, by1 = P.rect(b)
    if abs(ay1 - by0) < 1e-3 or abs(by1 - ay0) < 1e-3:
        y = ay1 if abs(ay1 - by0) < 1e-3 else ay0; lo, hi = max(ax0, bx0), min(ax1, bx1)
        assert hi - lo > 100, (a, b, lo, hi); return [round((lo + hi) / 2, 1), round(y, 1)]
    if abs(ax1 - bx0) < 1e-3 or abs(bx1 - ax0) < 1e-3:
        x = ax1 if abs(ax1 - bx0) < 1e-3 else ax0; lo, hi = max(ay0, by0), min(ay1, by1)
        assert hi - lo > 100, (a, b, lo, hi); return [round(x, 1), round((lo + hi) / 2, 1)]
    raise SystemExit(f'{a} {b} do not abut')
moved = ('s_2N_L0', 's_3N_L0', 's_4N_L0')
for k in [k for k in tap if any(m in k.split('->') for m in moved)]:
    del tap[k]
new = {'s_3N_L0': 's_2N_L2', 's_2N_C': 's_3N_L0', 's_4N_L2': 's_3N_L0', 's_2N_L0': 's_1N_x06', 's_4N_L0': 's_5N_L4'}
for c, p in new.items():
    par[c] = p
for c, p in par.items():
    if p and (c in moved or p in moved):
        tap[f'{p}->{c}'] = shared(p, c)
# tree sanity: every part reaches the root, no cycle
for c in par:
    seen, q = set(), c
    while par[q] is not None:
        assert q not in seen, ('cycle', c); seen.add(q); q = par[q]
    assert q == f['root'], c
assert set(par) == set(P.parts), set(par) ^ set(P.parts)
for k in tap:
    a, b = k.split('->'); assert par[b] == a, k
print({k: v for k, v in tap.items() if any(m in k.split('->') for m in moved)})
json.dump(f, open(sys.argv[3], 'w'))
