#!/usr/bin/env python3
"""FT-HBM lane census v2 (estimate): per (lane, destination) path = tail relay row back to its head row along the deepest predecessor.
Distance uses head/tail relay row centroids (relays sit at the endpoint pins). Straight L between them (HV or VH, fewer big-block um),
per-big-block crossing (face in/out, bits), stage counts now vs ceil(L/hop)."""
import json, re, sys, collections, math
C = json.load(open(sys.argv[1])); tsv = sys.argv[2]; out = sys.argv[3]
P = {}
for l in open(tsv):
    f = l.rstrip('\n').split('\t'); P[f[0]] = dict(m=f[1], x=float(f[2]), y=float(f[3]), w=float(f[4]), h=float(f[5]))
BIG = {n: p for n, p in P.items() if max(p['w'], p['h']) >= 450 and not p['m'].startswith('hbfd_')}
def row(i): return re.sub(r'_l\d+$', '', i)
rows = collections.defaultdict(list)
for i in C: rows[row(i)].append(i)
succ = collections.defaultdict(set); pred = collections.defaultdict(set)
for i, r in C.items():
    for j in r['dn']:
        if row(j) != row(i): succ[row(i)].add(row(j)); pred[row(j)].add(row(i))
def cent(r):
    xs = [C[i]['xy'] for i in rows[r] if C[i]['xy']]
    return (sum(p[0] + p[2] / 2 for p in xs) / len(xs), sum(p[1] + p[3] / 2 for p in xs) / len(xs)) if xs else None
bits = {r: sum(C[i]['bits'] for i in rows[r]) for r in rows}
dmemo = {}
def depth(r, stack=()):
    if r in dmemo: return dmemo[r]
    ps = [p for p in pred[r] if p not in stack]
    if not ps: dmemo[r] = (1, r); return dmemo[r]
    best = max((depth(p, stack + (r,)) for p in ps), key=lambda t: t[0])
    dmemo[r] = (best[0] + 1, best[1]); return dmemo[r]
sys.setrecursionlimit(100000)
def seg_cross(p, q, b):
    x0, y0, x1, y1 = b['x'], b['y'], b['x'] + b['w'], b['y'] + b['h']
    if abs(p[1] - q[1]) < 1e-6:
        y = p[1]
        if not (y0 < y < y1): return 0, None
        lo, hi = sorted((p[0], q[0])); t = max(0, min(hi, x1) - max(lo, x0))
        return t, ('WE' if q[0] > p[0] else 'EW') if lo < x0 and hi > x1 else None
    x = p[0]
    if not (x0 < x < x1): return 0, None
    lo, hi = sorted((p[1], q[1])); t = max(0, min(hi, y1) - max(lo, y0))
    return t, ('SN' if q[1] > p[1] else 'NS') if lo < y0 and hi > y1 else None
paths = []
for r in rows:
    if succ[r]: continue           # tails only
    d, h = depth(r)
    a, b = cent(h), cent(r)
    if not (a and b): continue
    src = collections.Counter(); dst = collections.Counter()
    for i in rows[h]: src.update(C[i]['src'])
    for i in rows[r]: dst.update(C[i]['dst'])
    man = abs(a[0] - b[0]) + abs(a[1] - b[1])
    best = None
    for k, mid in (('HV', (b[0], a[1])), ('VH', (a[0], b[1]))):
        cr = {}
        for n, bb in BIG.items():
            t1, f1 = seg_cross(a, mid, bb); t2, f2 = seg_cross(mid, b, bb)
            if t1 + t2 > 1: cr[n] = dict(um=round(t1 + t2), through=f1 or f2)
        tot = sum(v['um'] for v in cr.values())
        if best is None or tot < best[2]: best = (k, cr, tot)
    paths.append(dict(tail=r, head=h, stages=d, bits=bits[r], src=src.most_common(1)[0][0] if src else None,
                      dst=dst.most_common(1)[0][0] if dst else None, a=[round(v) for v in a], b=[round(v) for v in b],
                      manh_um=round(man), L=best[0], cross=best[1], cross_um=best[2],
                      s1000=max(1, math.ceil(man / 1000)), s1200=max(1, math.ceil(man / 1200)), fam=C[rows[r][0]]['m']))
json.dump(paths, open(out, 'w'))
S = lambda k: sum(p[k] for p in paths)
print('paths', len(paths), 'stages now', S('stages'), '@1.0', S('s1000'), '@1.2', S('s1200'))
# v2b: current-route polyline length (deepest predecessor walk) -> stages at 1.0 mm along the CURRENT route vs straight
for p in paths:
    r = p['tail']; seq = [r]; seen = {r}
    while pred[r]:
        q = [x for x in pred[r] if x not in seen]
        if not q: break
        r = max(q, key=lambda x: depth(x)[0]); seq.append(r); seen.add(r)
    pts = [cent(x) for x in reversed(seq)]
    pts = [q for q in pts if q]
    L = sum(abs(a[0] - b[0]) + abs(a[1] - b[1]) for a, b in zip(pts, pts[1:]))
    p['route_um'] = round(L)
    p['r1000'] = max(1, math.ceil(L / 1000)); p['r1200'] = max(1, math.ceil(L / 1200))
json.dump(paths, open(out, 'w'))
print('stages @1.0 along current routes', sum(p['r1000'] for p in paths), '@1.2', sum(p['r1200'] for p in paths))
