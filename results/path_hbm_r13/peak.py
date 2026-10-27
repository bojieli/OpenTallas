import sys, json, numpy as np, collections
P = json.load(open(sys.argv[1] + '/die_plan.json')); tn = sys.argv[2]; f0 = sys.argv[3]
t = P['partition_types'][tn]; W, H = t['outline_um']; pts = {}; who = collections.defaultdict(set)
for s in t['internal_stations']:
    for p in (s['from_um'], s['to_um']):
        if p[1] <= .5 or p[1] >= H - .5:
            k = ('S' if p[1] <= .5 else 'N', round(p[0], 3)); pts[k] = max(pts.get(k, 0), s.get('bits_parallel', s['bits']))
            who[k].add((s['conn'], s.get('r13', ''), 'fa' if s.get('r13_face_affine') else ''))
d = np.zeros(int(W) + 2); items = []
for (ff, x), b in pts.items():
    if ff != f0: continue
    a = x - b / 12; c = x + b / 12; d[max(0, int(np.floor(a))):int(np.ceil(c))] += 6; items.append((a, c, b, x, who[(ff, x)]))
g = np.convolve(d, np.ones(4) / 4, 'same'); i = int(g.argmax()); print('peak', g.max(), 'at', i)
for a, c, b, x, w in sorted(items):
    if a <= i + 2 and c >= i - 2: print(round(a), round(c), b, x, list(w)[:3])
