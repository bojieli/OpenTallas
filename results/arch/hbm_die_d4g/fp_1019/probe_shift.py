#!/usr/bin/env python3
"""L2H-GEN2D-FP PROBE (not a release artifact): shift hb_dbk/hc blocks by +-43.2 um in x in a placed manifest and
cascade-shift small lane relays (<=64.8 um) that the moved blocks then overlap (same dx, repeated until clean).
Big blocks hit by the cascade are reported (probe fails). Usage: probe_shift.py in.json out.json"""
import json, sys
m = json.load(open(sys.argv[1])); pl = m['placement']
D = 43.2
seed = {'hb_dbk_NW': D, 'hc_NW': D, 'hb_dbk_SW': D, 'hc_SW': D, 'hc_NE': -D, 'hc_SE': -D}
BIN = 200.0
bins = {}
def keys(v):
    for i in range(int(v['x'] // BIN), int((v['x'] + v['w']) // BIN) + 1):
        for j in range(int(v['y'] // BIN), int((v['y'] + v['h']) // BIN) + 1):
            yield (i, j)
def add(n):
    for k in keys(pl[n]): bins.setdefault(k, set()).add(n)
def rem(n):
    for k in keys(pl[n]): bins.get(k, set()).discard(n)
for n in pl: add(n)
def ov(n):
    v = pl[n]; out = set()
    for k in keys(v):
        for o in bins.get(k, ()):
            if o == n: continue
            u = pl[o]
            if u['x'] < v['x'] + v['w'] - 1e-6 and u['x'] + u['w'] > v['x'] + 1e-6 and u['y'] < v['y'] + v['h'] - 1e-6 and u['y'] + u['h'] > v['y'] + 1e-6:
                out.add(o)
    return out
moved = {}; bad = []; queue = list(seed.items()); hit = []
while queue:   # big blocks: cascade the same dx; small lane relays: collected, relocated afterwards
    n, dx = queue.pop(0)
    if n in moved: continue
    rem(n); pl[n]['x'] = round(pl[n]['x'] + dx, 4); add(n); moved[n] = dx
    pl[n]['rule'] = pl[n].get('rule', '') + f' | FP-PROBE shift {dx:+.1f}'
    for o in ov(n):
        if max(pl[o]['w'], pl[o]['h']) > 64.8:
            if o in moved: bad.append((n, o, 'already moved')); continue
            queue.append((o, dx))
        else: hit.append(o)
STEP = 2.16
relocated = {}
# keep-out: the widened channels themselves (relocated relays must not refill them)
KO = []
for q, sf, blk in (('NW', 'sfucore_NW', ['hb_dbk_NW', 'hc_NW']), ('SW', 'sfucore_SW', ['hb_dbk_SW', 'hc_SW'])):
    s_ = pl[sf]; KO.append((s_['x'] + s_['w'], min(pl[b]['x'] for b in blk), s_['y'], s_['y'] + s_['h']))
for q in ('NE', 'SE'):
    s_ = pl['sfucore_' + q]; h_ = pl['hc_' + q]; KO.append((h_['x'] + h_['w'], s_['x'], s_['y'], s_['y'] + s_['h']))
def inko(o):
    v = pl[o]
    return any(v['x'] < x1 and v['x'] + v['w'] > x0 and v['y'] < y1 and v['y'] + v['h'] > y0 for x0, x1, y0, y1 in KO)
def free(o):
    return not inko(o) and not ov(o) and pl[o]['x'] >= 0 and pl[o]['y'] >= 0 and pl[o]['x'] + pl[o]['w'] <= m['die_um'][0] and pl[o]['y'] + pl[o]['h'] <= m['die_um'][1]
for o in sorted(set(hit)):
    if not ov(o): continue
    x0, y0 = pl[o]['x'], pl[o]['y']; done = False
    rem(o)
    for r in range(1, 250):
        for a in range(-r, r + 1):
            for dx, dy in ((a * STEP, (r - abs(a)) * STEP), (a * STEP, -(r - abs(a)) * STEP)):
                pl[o]['x'], pl[o]['y'] = round(x0 + dx, 4), round(y0 + dy, 4)
                if free(o): done = True; break
            if done: break
        if done: break
    if not done: pl[o]['x'], pl[o]['y'] = x0, y0; bad.append((o, 'no free spot', pl[o]['m']))
    else:
        relocated[o] = (round(pl[o]['x'] - x0, 3), round(pl[o]['y'] - y0, 3))
        pl[o]['rule'] = pl[o].get('rule', '') + f' | FP-PROBE relocated {relocated[o]}'
    add(o)
x_out = [n for n in moved if pl[n]['x'] < 0 or pl[n]['x'] + pl[n]['w'] > m['die_um'][0]]
m['label'] = str(m.get('label')) + ' FP-PROBE (not a release artifact)'
m['fp_probe'] = dict(keepout=KO, seed=seed, moved=len(moved), cascade=sorted(set(moved) - set(seed)), relocated=relocated, collisions=bad, off_die=x_out)
json.dump(m, open(sys.argv[2], 'w'))
print('PROBE moved', len(moved), sorted(set(moved)-set(seed)), 'relocated', len(relocated), 'max_disp', max((abs(a)+abs(b) for a,b in relocated.values()), default=0), 'collisions', len(bad), bad[:10], 'off_die', x_out)
