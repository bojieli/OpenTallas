"""DS85: die-clock feed for plan_h2_2249 = the DIE-S81-13 sb6 feed TREE (results/die_s81_13_1028/data/sb6.json parent
map, all 398 parts present) with every feed tap re-derived on the CURRENT plan geometry by the feed tool's convention
(feed_a3_1031.py: tap at the middle of the parent/child shared edge).  usage: feed_h2.py SB6 PLAN TOOLS OUT"""
import json, sys
sys.path.insert(0, sys.argv[3])
import schema as S
f = json.load(open(sys.argv[1])); P = S.Plan(S.load(sys.argv[2]), sys.argv[2])
par = f['parent']
TOL = 60.0   # um: a channel/street gap still counts as a neighbour (tap on the gap midline)
def shared(a, b, tol=1e-3):
    ax0, ay0, ax1, ay1 = P.rect(a); bx0, by0, bx1, by1 = P.rect(b)
    for g, y in ((by0 - ay1, (ay1 + by0) / 2), (ay0 - by1, (ay0 + by1) / 2)):
        if -1e-3 < g < tol:
            lo, hi = max(ax0, bx0), min(ax1, bx1)
            if hi - lo > 0: return [round((lo + hi) / 2, 1), round(y, 1)], hi - lo
    for g, x in ((bx0 - ax1, (ax1 + bx0) / 2), (ax0 - bx1, (ax0 + bx1) / 2)):
        if -1e-3 < g < tol:
            lo, hi = max(ay0, by0), min(ay1, by1)
            if hi - lo > 0: return [round(x, 1), round((lo + hi) / 2, 1)], hi - lo
    return None, 0
def depth(n):
    k = 0
    while par[n] is not None:
        n = par[n]; k += 1
    return k
def subtree(c):
    out = {c}; ch = True
    while ch:
        ch = False
        for k, v in par.items():
            if v in out and k not in out:
                out.add(k); ch = True
    return out
def ctr(n):
    x0, y0, x1, y1 = P.rect(n); return (x0 + x1) / 2, (y0 + y1) / 2
# rebuild as a spanning tree of the abutment graph from the sb6 root: every sb6 edge that still abuts is kept; a part
# whose sb6 parent no longer abuts (or is not yet attached) joins the attached abutting neighbour of least feed depth
# (tie: nearest to its old parent).  Repeated until all parts are attached.
old = dict(par)
nb = {n: [m for m in P.parts if m != n and shared(m, n)[0] is not None] for n in P.parts}
newpar, dep = {f['root']: None}, {f['root']: 0}
reparent = []
while len(newpar) < len(P.parts):
    grew = False
    for c in sorted(P.parts):
        if c in newpar: continue
        p0 = old.get(c)
        if p0 in newpar and p0 in nb[c]:
            newpar[c] = p0; dep[c] = dep[p0] + 1; grew = True; continue
    if grew: continue
    best = None
    for c in sorted(P.parts):
        if c in newpar: continue
        att = [m for m in nb[c] if m in newpar]
        if not att: continue
        px, py = ctr(old[c]) if old.get(c) else ctr(c)
        m = min(att, key=lambda m: (dep[m], abs(ctr(m)[0] - px) + abs(ctr(m)[1] - py)))
        k = (dep[m], c)
        if best is None or k < best[0]: best = (k, c, m)
    if best is None: raise SystemExit('abutment graph disconnected: ' + str(sorted(set(P.parts) - set(newpar))[:10]))
    _, c, m = best
    newpar[c] = m; dep[c] = dep[m] + 1; reparent.append((c, old.get(c), m))
par = newpar
print('re-parented (child, old parent, new parent):', reparent)
tap, bad, short = {}, [], []
for c, p in par.items():
    if p is None: continue
    t, ov = shared(p, c)
    if t is None: t, ov = shared(p, c, TOL); short.append((p, c, 'gap-tap'))
    if t is None: bad.append((p, c)); continue
    if ov <= 100: short.append((p, c, round(ov, 1)))
    tap[f'{p}->{c}'] = t
for c in par:
    seen, q = set(), c
    while par[q] is not None:
        assert q not in seen; seen.add(q); q = par[q]
    assert q == f['root']
assert set(par) == set(P.parts), set(par) ^ set(P.parts)
print('edges', len(tap), 'non-abutting', bad, 'short overlap <=100um', short)
if bad: raise SystemExit('feed edges that no longer abut')
json.dump(dict(root=f['root'], parent=par, tap=tap, note='DS85 sb6 tree, taps re-derived on plan_h2_2249 geometry; non-abutting edges re-parented', reparented=reparent), open(sys.argv[4], 'w'), indent=0)
