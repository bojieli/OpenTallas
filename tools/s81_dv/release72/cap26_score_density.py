import json, sys, collections
# usage: dens.py routed_plan.json [tag]: H/V bit demand per 1-mm window from the routed station points (x-then-y legs)
p = json.load(open(sys.argv[1])); B = p['blocks']; D = collections.Counter()
def leg(a, b, bits):
    (x0, y0), (x1, y1) = a, b
    for (u0, v0, u1, v1, o) in ((x0, y0, x1, y0, 'H'), (x1, y0, x1, y1, 'V')):
        if o == 'H':
            lo, hi = sorted((u0, u1)); y = v0
            t = lo
            while t < hi:
                nx = min(hi, (int(t // 1000) + 1) * 1000); D[(int(t // 1000), int(y // 1000), 'H')] += bits * (nx - t) / 1000; t = nx
        else:
            lo, hi = sorted((v0, v1)); x = u0; t = lo
            while t < hi:
                ny = min(hi, (int(t // 1000) + 1) * 1000); D[(int(x // 1000), int(t // 1000), 'V')] += bits * (ny - t) / 1000; t = ny
for l in p['links']:
    if l.get('h') and len(l['h'][0]) == 5:
        for x0, y0, x1, y1, bb in l['h']:
            leg((x0, y0), (x1, y1), bb)
        continue
    pts = [tuple(l['e'][0][2:4])] + [tuple(q[:2]) for q in (l.get('sp') or [(h[2], h[3]) for h in l.get('h', [])[:-1]])] + [tuple(l['e'][1][2:4])]
    for a, b in zip(pts, pts[1:]):
        leg(a, b, l['b'])
top = D.most_common(8)
probe = {k: round(D.get(k, 0)) for k in [(7, 11, 'V'), (7, 12, 'V'), (8, 11, 'V'), (9, 17, 'H'), (9, 17, 'V'), (20, 17, 'H'), (20, 17, 'V'), (12, 17, 'H'), (25, 11, 'H')]}
print(sys.argv[2] if len(sys.argv) > 2 else '', 'bitmm', round(sum(D.values())), 'top', ' '.join(f'{a},{b}{o}:{round(v)}' for (a, b, o), v in top), '| hot', ' '.join(f'{a},{b}{o}:{v}' for (a, b, o), v in probe.items()))
