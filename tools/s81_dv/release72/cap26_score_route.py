import json, sys, collections, re
# usage: summ.py route.log hot.json  -> one line: final ITER, ROUTE_DONE, hot(>=1.0) seg count, top windows by over-capacity demand
log, hot = sys.argv[1:3]
L = open(log).read().splitlines()
it = [l for l in L if l.startswith('ITER')][-1]; dn = [l for l in L if l.startswith('ROUTE_DONE')]
H = json.load(open(hot)); w = collections.Counter(); n = 0
for s in H:
    if s['ratio'] < 1.0: continue
    n += 1; x0, y0, x1, y1 = s['seg']; k = (int((x0 + x1) / 2000), int((y0 + y1) / 2000), s['o'])
    w[k] += (s['ratio'] - 1.0) * s['cap'] * max(abs(x1 - x0), abs(y1 - y0)) / 1000.0
tot = sum(w.values())
print(sys.argv[3] if len(sys.argv) > 3 else hot, '|', it, '|', dn[0] if dn else 'NO ROUTE_DONE', '| hot_segs', n, 'over_bitmm', round(tot), '| top', ' '.join(f'{a},{b}{o}:{round(v)}' for (a, b, o), v in w.most_common(6)))
