import json, sys, ast, collections
d = json.load(open(sys.argv[1]))
I = {i['name']: i for i in d['insts']}
def ctr(n):
    i = I.get(n); return None if i is None else (i['x'] + i['w'] / 2, i['y'] + i['h'] / 2)
# vertical channel strips in the SW SM group + the mid hub-edge channels; and SW spine channel
strips = {'SW_edge_x0': (365, 625), 'SW_col_ch1': (3839, 4099), 'SW_col_ch2': (7313, 7572), 'SW_grp_E': (10786, 11050),
          'W_spine_ch': (13492, 14736), 'E_spine_ch': (16136, 17380)}
Y = {'SW_edge_x0': (1467, 6322), 'SW_col_ch1': (1467, 6322), 'SW_col_ch2': (1467, 6322), 'SW_grp_E': (1467, 6322),
     'W_spine_ch': (6322, 18960), 'E_spine_ch': (6322, 18960)}
load = collections.defaultdict(collections.Counter)
for b in d['buses']:
    if b['cls'].startswith(('clock', 'reset', 'strap')): continue
    names = [ast.literal_eval(e)[0] if e.startswith('(') else e for e in b['eps']]
    cs = [ctr(n) for n in names]; cs = [c for c in cs if c]
    if len(cs) < 2: continue
    a, c = cs[0], cs[-1]
    for s, (x0, x1) in strips.items():
        y0, y1 = Y[s]
        ins = [p for p in (a, c) if x0 - 60 <= p[0] <= x1 + 60]
        if not ins: continue
        lo, hi = min(a[1], c[1]), max(a[1], c[1])
        if hi < y0 or lo > y1: continue
        if abs(a[1] - c[1]) > 150:
            load[s][b['cls']] += b['bits']
for s in strips:
    w = strips[s][1] - strips[s][0]
    cap = w * (0.7033 / 0.048 + 0.8531 / 0.064 + 0.85 / 0.080)
    tot = sum(load[s].values())
    print(s, 'width', round(w, 1), 'vert tracks (derated M5/M7/M9)', int(cap), 'bits', tot, 'use', round(tot / cap, 3), dict(load[s].most_common(6)))
