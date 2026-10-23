# FT-S81 10-23: input = cap24 plan.json (ep9 /srv/opentallas-scratch2/claude/stw-s81c-cap24-main/plan.json), env FT_S81_PLAN; quick estimate until tools/die_feedthrough census/plan land.
import json, collections
P = json.load(open(__import__('os').environ.get('FT_S81_PLAN', 'dump/plan.json'))); B = P['blocks']
big = [i for i, b in enumerate(B) if b['w'] * b['h'] >= 0.5e6]
def cross(seg, b):
    (x0, y0), (x1, y1) = seg; bx0, by0, bx1, by1 = b['x'], b['y'], b['x'] + b['w'], b['y'] + b['h']
    if y0 == y1:
        if not (by0 < y0 < by1): return None
        lo, hi = max(min(x0, x1), bx0), min(max(x0, x1), bx1); return ('H', hi - lo) if hi - lo > 1 else None
    if not (bx0 < x0 < bx1): return None
    lo, hi = max(min(y0, y1), by0), min(max(y0, y1), by1); return ('V', hi - lo) if hi - lo > 1 else None
H = collections.Counter(); V = collections.Counter(); per = collections.defaultdict(collections.Counter)
for L in P['links']:
    (si, _, sx, sy, _), (di, _, dx, dy, _) = L['e'][0], L['e'][1]
    sf, df = B[si]['name'].startswith('f_'), B[di]['name'].startswith('f_')
    if sf and not df:   # frame -> hub: H leg at frame y, V leg at hub x
        path = [((sx, sy), (dx, sy)), ((dx, sy), (dx, dy))]
    elif df and not sf:
        path = [((sx, sy), (sx, dy)), ((sx, dy), (dx, dy))]
    else:
        cands = ([((sx, sy), (dx, sy)), ((dx, sy), (dx, dy))], [((sx, sy), (sx, dy)), ((sx, dy), (dx, dy))])
        path = min(cands, key=lambda p: sum(1 for k in big if k not in (si, di) for s in p if cross(s, B[k])))
    for k in big:
        if k in (si, di): continue
        for s in path:
            c = cross(s, B[k])
            if c: per[B[k]['name']][c[0]] += L['b']
tot = collections.Counter()
for n, c in sorted(per.items(), key=lambda t: -sum(t[1].values())):
    b = next(x for x in B if x['name'] == n)
    print(f"{n:8s} {b['master']:24s} H {c['H']:6d} ({c['H']/(b['h']/0.08*0.92):.2f} M8)  V {c['V']:6d} ({c['V']/(b['w']/0.08*0.92):.2f} M9)")
