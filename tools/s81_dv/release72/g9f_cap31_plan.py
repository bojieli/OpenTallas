#!/usr/bin/env python3
"""S81 DIE72 cap31 floorplan = cap30 plan (cap29 MAIN + 5 rigid street re-slots) + rigid re-slots sized from the cap24 rep600
GRT maps (probe + 30-iteration residual) against the cap30 routed plan (STW-S81d-GEN, 10-22).

Street audit (streets.py on the cap30 routed plan: lane bits crossing the street / H tracks M4 14.58 + M6 14.06 + M8 11.25 per um,
V tracks M3+M5+M7+M9 55.0 per um; target <= 0.6), probe-confirmed windows, all on the 43.2-um lattice, rigid (no resize /
mirror / pin-face / interface change):
  y~10.5 row edge  rsv_01|s_0S 1.31, rsv_03|s_0S 1.29 (139.0 um)  -> s_0S + s_0N +172.8 N (s_0 centre street stays 777.6)
  y~17.5 top edge  s_7S|s_7N 0.94 (345.6 um)                       -> s_7N +216.0 N (561.6 um)
  x~7.7 V street   f_3L10|lk_WN3 1.60 (86.4 um, probe V at (6.5-7, 18.25)) -> lk_WN3 + lk_WN1 +172.8 E (259.2 um)
Checks (as g9f_cap30_plan.py): seal, >= 86.4 between all bodies + blockages, every endpoint on its face.
Usage: g9f_cap31_plan.py CAP26_PLAN OUT [--only NAME,...] [--no-cap30]
"""
import argparse, json
from pathlib import Path

SEAL, GAP = 100.0, 86.4
CAP30 = {'s_0N': (0.0, 172.8), 's_1S': (0.0, 216.0), 'bk_col': (0.0, 216.0), 's_6N': (0.0, -129.6),
         'lk_WN0': (86.4, 0.0), 'lk_WN2': (86.4, 0.0),
         'lk_EN0': (-129.6, 0.0), 'lk_EN1': (-129.6, 0.0), 'link_1_4': (-129.6, 0.0), 'link_1_5': (-129.6, 0.0)}
CAP31 = {'s_0S': (0.0, 172.8), 's_0N': (0.0, 172.8), 's_7N': (0.0, 216.0), 'lk_WN3': (172.8, 0.0), 'lk_WN1': (172.8, 0.0)}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('plan'); ap.add_argument('out'); ap.add_argument('--only', default='')
    ap.add_argument('--no-cap30', action='store_true')
    v = ap.parse_args(); p = json.load(open(v.plan)); W, H = p['facts']['die_um']
    assert 'cap26' in p['facts']['physical72'], 'input must be a cap26 plan'
    allr = p['blocks'] + p.get('blockages', [])
    by = {b['name']: b for b in allr}
    move = {} if v.no_cap30 else {n: list(d) for n, d in CAP30.items()}
    for n, (dx, dy) in CAP31.items():
        if not v.only or n in v.only.split(','):
            d = move.setdefault(n, [0.0, 0.0]); d[0] = round(d[0] + dx, 4); d[1] = round(d[1] + dy, 4)
    miss = [n for n in move if n not in by]; assert not miss, ('unknown blocks', miss)
    for n, (dx, dy) in move.items():
        assert abs(dx / 43.2 - round(dx / 43.2)) < 1e-6 and abs(dy / 43.2 - round(dy / 43.2)) < 1e-6, ('off lattice', n)
    rec = {}
    for n, (dx, dy) in move.items():
        b = by[n]; rec[n] = dict(before=[round(b['x'], 4), round(b['y'], 4)])
        b['x'] = round(b['x'] + dx, 4); b['y'] = round(b['y'] + dy, 4); rec[n]['after'] = [b['x'], b['y']]
        b['scope'] = (b.get('scope', '') + f' | cap31: rigid street move ({dx:+.2f}, {dy:+.2f}) um from cap26 (incl. cap30), body/pins unchanged').strip(' |')
    bidx = {i: b['name'] for i, b in enumerate(p['blocks'])}
    for l in p['links']:
        for e in l['e']:
            n = bidx[e[0]]
            if n in move:
                e[2] = round(e[2] + move[n][0], 4); e[3] = round(e[3] + move[n][1], 4)
        for k in ('h', 'sp', 's', 'L', 'station_dirs'):
            l.pop(k, None)
    for l in p['links']:
        for e, f in zip(l['e'], l['endpoint_faces']):
            b = p['blocks'][e[0]]
            assert {'W': abs(e[2] - b['x']) < 1e-3, 'E': abs(e[2] - b['x'] - b['w']) < 1e-3, 'S': abs(e[3] - b['y']) < 1e-3,
                    'N': abs(e[3] - b['y'] - b['h']) < 1e-3}[f], (l['i'], e, f)
    for b in allr:
        assert min(b['x'], b['y']) >= SEAL - 1e-6 and b['x'] + b['w'] <= W - SEAL + 1e-6 and b['y'] + b['h'] <= H - SEAL + 1e-6, b['name']
    bad = []
    for i, b in enumerate(allr):
        for c in allr[i + 1:]:
            sep = max(c['x'] - (b['x'] + b['w']), b['x'] - (c['x'] + c['w']), c['y'] - (b['y'] + b['h']), b['y'] - (c['y'] + c['h']))
            if sep < GAP - 0.25:
                bad.append((b['name'], c['name'], round(sep, 3)))
    assert not bad, bad
    p['facts']['physical72']['cap30'] = dict(tool='g9f_cap31_plan.py', base='cap26 plan', moves={n: rec[n] for n in CAP30 if n in rec},
                                             rule='rigid street re-slots (DIE4-BLK B\' table)')
    p['facts']['physical72']['cap31'] = dict(tool='g9f_cap31_plan.py', base='cap26 plan + cap30 moves', moves=rec,
                                             rule='rigid street re-slots sized from cap24 rep600 GRT maps vs cap30 routed plan (streets.py, <= 0.6); no resize, no mirror, no pin/face/interface change')
    p['facts']['physical72']['routing'] = 'cap31 unrouted: dv_route72c.py required'
    Path(v.out).write_text(json.dumps(p, indent=1))
    print('CAP31_PLAN', json.dumps(rec))


if __name__ == '__main__':
    main()
