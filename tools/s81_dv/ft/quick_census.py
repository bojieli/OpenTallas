#!/usr/bin/env python3
"""FT-S81 quick crossing census (pre FT-TOOL): plan.json links -> Manhattan L-path -> big-block crossings."""
import json, sys, collections, math
P = json.load(open(sys.argv[1])); REACH = float(sys.argv[2]) if len(sys.argv) > 2 else 1500.0
blocks = P['blocks']; links = P['links']
BIG = 0.5e6   # um2
def inside_seg(seg, b):
    """length of an axis-parallel segment strictly inside block b, and entry/exit faces"""
    (x0, y0), (x1, y1) = seg
    bx0, by0, bx1, by1 = b['x'], b['y'], b['x'] + b['w'], b['y'] + b['h']
    if y0 == y1:   # horizontal
        if not (by0 < y0 < by1): return 0, None
        lo, hi = max(min(x0, x1), bx0), min(max(x0, x1), bx1)
        return (hi - lo, 'H') if hi > lo else (0, None)
    if not (bx0 < x0 < bx1): return 0, None
    lo, hi = max(min(y0, y1), by0), min(max(y0, y1), by1)
    return (hi - lo, 'V') if hi > lo else (0, None)
big = [i for i, b in enumerate(blocks) if b['w'] * b['h'] >= BIG]
res = collections.defaultdict(lambda: {'H': 0, 'V': 0, 'Hl': 0, 'Vl': 0, 'links': 0})
tot = collections.Counter(); per_cls = collections.defaultdict(collections.Counter)
rows = []
for L in links:
    if len(L.get('e', [])) < 2: continue
    (si, _, sx, sy, _), (di, _, dx, dy, _) = L['e'][0], L['e'][1]
    b = L['b']; man = abs(sx - dx) + abs(sy - dy)
    best = None
    for path in ([((sx, sy), (dx, sy)), ((dx, sy), (dx, dy))], [((sx, sy), (sx, dy)), ((sx, dy), (dx, dy))]):
        cr = []
        for k in big:
            if k in (si, di): continue
            for seg in path:
                ln, d = inside_seg(seg, blocks[k])
                if ln > 1.0: cr.append((k, d, ln))
        n = len({c[0] for c in cr})
        if best is None or n < best[0]: best = (n, cr)
    n, cr = best
    for k, d, ln in cr:
        r = res[blocks[k]['name']]; r[d] += b; r[d + 'l'] = max(r[d + 'l'], ln); r['links'] += 1
    cur_s = L.get('s', 0); new_s = max(0, math.ceil(man / REACH) - 1)
    tot['links'] += 1; tot['bits'] += b; tot['cur_bitstages'] += b * cur_s; tot['new_bitstages'] += b * new_s
    tot['cur_stages'] += cur_s; tot['new_stages'] += new_s
    tot['bits_crossing'] += b if cr else 0; tot['cur_bit_mm'] += b * L.get('L', man) / 1000; tot['man_bit_mm'] += b * man / 1000
    pc = per_cls[L['c']]; pc['n'] += 1; pc['bits'] += b; pc['cur_s_max'] = max(pc['cur_s_max'], cur_s); pc['new_s_max'] = max(pc['new_s_max'], new_s)
    pc['cur_s_sum'] += cur_s; pc['new_s_sum'] += new_s; pc['cross_bits'] += b if cr else 0; pc['nblk_cross'] += n
    rows.append((L['i'], L['c'], b, round(man), round(L.get('L', 0)), cur_s, new_s, n))
out = {'reach_um': REACH, 'totals': dict(tot), 'per_class': {k: dict(v) for k, v in per_cls.items()}, 'blocks': {}}
for name, r in res.items():
    b = next(x for x in blocks if x['name'] == name)
    # H crossing enters W/E faces (face length = h); M8 horizontal pitch 0.08 um, ~8% PG -> usable tracks
    trH = b['h'] / 0.08 * 0.92; trV = b['w'] / 0.08 * 0.92
    out['blocks'][name] = dict(master=b.get('master'), kind=b.get('kind'), w=b['w'], h=b['h'], H_bits=r['H'], V_bits=r['V'],
                               H_ratio_M8=round(r['H'] / trH, 3), V_ratio_M9=round(r['V'] / trV, 3), links=r['links'])
json.dump(out, open(sys.argv[3] if len(sys.argv) > 3 else '/dev/stdout', 'w'), indent=1)
with open((sys.argv[3] if len(sys.argv) > 3 else 'x') + '.links.tsv', 'w') as f:
    f.write('link\tclass\tbits\tmanhattan_um\tcur_len_um\tcur_stages\tnew_stages\tblocks_crossed\n')
    for r in rows: f.write('\t'.join(map(str, r)) + '\n')
