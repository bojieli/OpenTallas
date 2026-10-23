# FT-S81 10-23: input = cap24 plan.json (ep9 /srv/opentallas-scratch2/claude/stw-s81c-cap24-main/plan.json), env FT_S81_PLAN; quick estimate until tools/die_feedthrough census/plan land.
"""FT-S81 stage-count model for the static-schedule re-derivation (draft until FT-TOOL plan.py lands).
Row-aligned policy (frame<->hub lanes: H leg at the frame pin y, V leg at the hub face x), relay hop <= REACH,
ft rule A = registered in AND out in every crossed block (2 forced stations), rule B = in only (1 forced)."""
import json, collections, math, sys
P = json.load(open(__import__('os').environ.get('FT_S81_PLAN', 'dump/plan.json'))); B = P['blocks']; REACH = 1500.0
big = [i for i, b in enumerate(B) if b['w'] * b['h'] >= 0.5e6]
def span(seg, b):
    (x0, y0), (x1, y1) = seg; bx0, by0, bx1, by1 = b['x'], b['y'], b['x'] + b['w'], b['y'] + b['h']
    if y0 == y1:
        if not (by0 < y0 < by1): return None
        lo, hi = max(min(x0, x1), bx0), min(max(x0, x1), bx1)
        if hi - lo <= 1: return None
        return (lo - min(x0, x1), hi - min(x0, x1)) if x1 >= x0 else (max(x0, x1) - hi, max(x0, x1) - lo)
    if not (bx0 < x0 < bx1): return None
    lo, hi = max(min(y0, y1), by0), min(max(y0, y1), by1)
    if hi - lo <= 1: return None
    return (lo - min(y0, y1), hi - min(y0, y1)) if y1 >= y0 else (max(y0, y1) - hi, max(y0, y1) - lo)
def stations(forced, total):
    pts = sorted(set([0.0] + forced + [total])); n = 0
    for a, b in zip(pts, pts[1:]): n += max(0, math.ceil((b - a) / REACH) - 1)
    return n + len(set(forced))
out = {}; agg = collections.Counter(); cls = collections.defaultdict(lambda: [0, 0, 0, 0, 0])
for L in P['links']:
    (si, _, sx, sy, _), (di, _, dx, dy, _) = L['e'][0], L['e'][1]
    sf, df = B[si]['name'].startswith('f_'), B[di]['name'].startswith('f_')
    A = [((sx, sy), (dx, sy)), ((dx, sy), (dx, dy))]; Bp = [((sx, sy), (sx, dy)), ((sx, dy), (dx, dy))]
    if sf and not df: path = A
    elif df and not sf: path = Bp
    else: path = min((A, Bp), key=lambda p: sum(1 for k in big if k not in (si, di) for s in p if span(s, B[k])))
    fa, fb, off, crossed = [], [], 0.0, []
    for s in path:
        ln = abs(s[0][0] - s[1][0]) + abs(s[0][1] - s[1][1])
        for k in big:
            if k in (si, di): continue
            sp = span(s, B[k])
            if sp: fa += [off + sp[0], off + sp[1]]; fb += [off + sp[0]]; crossed.append(B[k]['name'])
        off += ln
    na, nb = stations(fa, off), stations(fb, off)
    out[L['i']] = dict(cls=L['c'], bits=L['b'], cur_stations=L.get('s', 0), manhattan_um=round(off), crossed=crossed,
                       stations_ruleA=na, stations_ruleB=nb)
    c = cls[L['c']]; c[0] = max(c[0], L.get('s', 0)); c[1] = max(c[1], na); c[2] = max(c[2], nb); c[3] += L['b'] * L.get('s', 0); c[4] += L['b'] * na
    agg['cur'] += L.get('s', 0); agg['A'] += na; agg['B'] += nb; agg['bit_cur'] += L['b'] * L.get('s', 0); agg['bit_A'] += L['b'] * na; agg['bit_B'] += L['b'] * nb
print(dict(agg))
for k, v in sorted(cls.items(), key=lambda t: -t[1][3]): print(f"{k:8s} max stations cur {v[0]:4d}  ruleA {v[1]:3d}  ruleB {v[2]:3d}   bit-stations cur {v[3]:8d} -> A {v[4]:8d}")
json.dump({'schema': 'ft_s81.stage_model.v0', 'reach_um': REACH, 'policy': __doc__, 'totals': dict(agg), 'lanes': out}, open(sys.argv[1], 'w'), indent=0)
