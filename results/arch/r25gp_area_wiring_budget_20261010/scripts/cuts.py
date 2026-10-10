import json, sys, ast, collections
d = json.load(open(sys.argv[1]))
I = {i['name']: i for i in d['insts']}
def ctr(n):
    i = I.get(n)
    return None if i is None else (i['x'] + i['w'] / 2, i['y'] + i['h'] / 2)
bits_by = collections.Counter()
peer = collections.defaultdict(collections.Counter)
X_W, X_E = 14100.0, 16760.0   # mid of W / E spine side channels
HY = (6322.32, 18960.48)
crossW = collections.Counter(); crossE = collections.Counter()
for b in d['buses']:
    if b['cls'].startswith(('clock', 'reset', 'strap')): continue
    eps = [ast.literal_eval(e) if e.startswith('(') else (e, '') for e in b['eps']]
    names = [e[0] for e in eps]
    for n in set(names): bits_by[n] += b['bits']
    for n in set(names):
        for m_ in set(names):
            if n != m_: peer[n][m_] += b['bits']
    cs = [ctr(n) for n in names]; cs = [c for c in cs if c]
    if len(cs) < 2: continue
    a, c = cs[0], cs[-1]
    for X, cnt in ((X_W, crossW), (X_E, crossE)):
        if (a[0] - X) * (c[0] - X) < 0:
            # crossing y: the endpoint inside the spine column if any, else the mean
            sp = [p for p in (a, c) if 14736 <= p[0] <= 16136]
            y = sp[0][1] if sp else (a[1] + c[1]) / 2
            if HY[0] <= y <= HY[1]:
                cnt[int((y - HY[0]) // 1000)] += b['bits']
rows = []
for n, bt in bits_by.items():
    i = I.get(n)
    if not i or i['kind'] in ('waypoint',): continue
    per = 2 * (i['w'] + i['h'])
    rows.append((n, i['master'], round(i['w'], 1), round(i['h'], 1), bt, round(per, 1), round(bt * 0.048 / per, 3)))
rows.sort(key=lambda r: -r[6])
json.dump(dict(blocks=rows, crossW=crossW, crossE=crossE, peer={k: dict(v) for k, v in peer.items() if k.startswith('hb_')}), open(sys.argv[2], 'w'), indent=0)
for r in rows[:40]: print(*r)
print('crossW', sorted(crossW.items())); print('crossE', sorted(crossE.items()))
