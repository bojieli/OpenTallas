# shelf packing of the svc_lo glue+closure macros in a full-width band of the 1442.88-um svc outline
W = 1442.88; HX = 11.5
M = {'160x256': (92.040, 39.432), '160x265': (94.824, 40.776), '256x256m1': (92.664, 41.352), '32x128': (51.432, 20.808),
     '1024x256': (174.744, 70.488), 'p192': (114.480, 100.710), '32x64': (31.968, 17.280), '768x256': (170.664, 55.896),
     '1024x35': (57.672, 42.936), '1024x39': (62.424, 42.936), '128x23': (21.384, 27.576)}
base = {'160x256': 12, '160x265': 8, '256x256m1': 4, '32x128': 17, 'p192': 8, '32x64': 4}
old = dict(base, **{'1024x256': 13})
new = dict(base, **{'256x256m1': 10, '768x256': 4, '1024x35': 1, '1024x39': 1, '128x23': 1})
hi = {'160x256': 12, '160x265': 8, '256x256m1': 4, '32x128': 17, '32x64': 4}
def pack(cnt, vy):
    items = sorted([M[k] for k, n in cnt.items() for _ in range(n)], key=lambda m: (-m[1], -m[0]))
    rows = []
    for w, h in items:
        for r in rows:   # first fit
            if r['x'] + w <= W + 1e-6 and h <= r['h']: r['x'] += w + HX; r['n'] += 1; break
        else: rows.append(dict(x=w + HX, h=h, n=1))
    return sum(r['h'] for r in rows) + vy * len(rows), [(round(r['h'], 1), r['n'], round(r['x'] - HX, 1)) for r in rows]
for name, c in (('svc_lo old idx', old), ('svc_lo idx fit', new), ('svc_hi', hi)):
    area = sum(M[k][0] * M[k][1] * n for k, n in c.items())
    for vy in (5.0, 10.8):
        h, rows = pack(c, vy); print('%-15s vgap %4.1f band %6.1f um  area %.1fk  rows %s' % (name, vy, h, area / 1e3, rows))
