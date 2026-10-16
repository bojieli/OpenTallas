import json, sys, ast, collections
d = json.load(open(sys.argv[1]))
I = {i['name']: i for i in d['insts']}
def ctr(n):
    i = I.get(n); return None if i is None else (i['x'] + i['w'] / 2, i['y'] + i['h'] / 2)
V_DER = 0.7033 / 0.048 + 0.8531 / 0.064 + 0.85 / 0.080      # derated vertical tracks / um (M5, M7, M9; GRT die run)
H_DER = 0.7065 / 0.048 + 0.8525 / 0.064 + 0.8499 / 0.080    # derated horizontal tracks / um (M4, M6, M8)
segs = []
for b in d['buses']:
    if b['cls'].startswith(('clock', 'reset', 'strap')): continue
    names = [ast.literal_eval(e)[0] if e.startswith('(') else e for e in b['eps']]
    cs = [ctr(n) for n in names]; cs = [c for c in cs if c]
    if len(cs) < 2: continue
    segs.append((cs[0], cs[-1], b['bits'], b['cls']))
def vstrip(x0, x1, y0, y1, step=100):
    best = (0, None, None)
    prof = []
    y = y0
    while y <= y1:
        tot = 0; cl = collections.Counter()
        for a, c, bits, cls in segs:
            lo, hi = min(a[1], c[1]), max(a[1], c[1])
            if not (lo <= y <= hi): continue
            # vertical leg: at the x of either end (L route), count if that x is in the strip
            if any(x0 - 60 <= p[0] <= x1 + 60 for p in (a, c)) and abs(a[1] - c[1]) > 150:
                tot += bits; cl[cls] += bits
        prof.append((y, tot))
        if tot > best[0]: best = (tot, y, dict(cl.most_common(6)))
        y += step
    return best, prof
def hstrip(y0, y1, x0, x1, step=100):
    best = (0, None, None); x = x0
    while x <= x1:
        tot = 0; cl = collections.Counter()
        for a, c, bits, cls in segs:
            lo, hi = min(a[0], c[0]), max(a[0], c[0])
            if not (lo <= x <= hi): continue
            if any(y0 - 60 <= p[1] <= y1 + 60 for p in (a, c)) and abs(a[0] - c[0]) > 150:
                tot += bits; cl[cls] += bits
        if tot > best[0]: best = (tot, x, dict(cl.most_common(6)))
        x += step
    return best
out = {}
V = {'SW_edge_x0': (365, 625, 1467, 6322), 'SW_col_ch1': (3839, 4099, 1467, 6322), 'SW_col_ch2': (7313, 7572, 1467, 6322),
     'SW_grp_E': (10786, 11050, 1467, 6322), 'W_spine_ch': (13492, 14736, 6322, 18960), 'E_spine_ch': (16136, 17380, 6322, 18960),
     'SW_idx_hc_gap': (9700, 10046, 6322, 11852), 'SW_hc_sfu_gap': (10597, 10943, 6322, 11852), 'SW_sfu_su_gap': (11740, 12086, 6322, 11852)}
for k, (x0, x1, y0, y1) in V.items():
    (tot, y, cl), prof = vstrip(x0, x1, y0, y1)
    cap = (x1 - x0) * V_DER
    out[k] = dict(kind='vertical', x=[x0, x1], width_um=x1 - x0, tracks_derated=int(cap), max_bits=tot, at_y=y,
                  use=round(tot / cap, 3), top=cl)
    print(k, out[k])
H = {'hub_S_edge_ch(SM N row->hub)': (5772, 6322, 365, 31368), 'SM_row_ch_520': (2728, 3248, 365, 31368), 'SM_row_ch_259': (4380, 4639, 365, 31368)}
for k, (y0, y1, x0, x1) in H.items():
    tot, x, cl = hstrip(y0, y1, x0, x1)
    cap = (y1 - y0) * H_DER
    out[k] = dict(kind='horizontal', y=[y0, y1], width_um=y1 - y0, tracks_derated=int(cap), max_bits=tot, at_x=x,
                  use=round(tot / cap, 3), top=cl)
    print(k, out[k])
json.dump(dict(V_DER=V_DER, H_DER=H_DER, channels=out), open(sys.argv[2], 'w'), indent=1)
