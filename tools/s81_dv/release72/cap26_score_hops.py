import json, sys
p = json.load(open(sys.argv[1])); worst = []
for l in p['links']:
    sp = l.get('sp') or []
    pts = [tuple(l['e'][0][2:4])] + [tuple(q[:2]) for q in sp] + [tuple(l['e'][1][2:4])]
    for i, (a, b) in enumerate(zip(pts, pts[1:])):
        d = abs(a[0] - b[0]) + abs(a[1] - b[1])
        if d > 405: worst.append((round(d, 1), l['i'], i))
worst.sort(reverse=True); print(sys.argv[1], 'manhattan>405:', len(worst), worst[:5])
