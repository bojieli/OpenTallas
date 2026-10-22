#!/usr/bin/env python3
"""S81 DIE72 cap19 floorplan successor of Codex cap18 (528fc3c9f) -- STW-S81c-DIE-CAP 10-22.

Input = the cap17/cap18 plan (pool body already reserved); routing keys are stripped, every listed block is moved
RIGIDLY (no resize, no body shrink, no pin-face change: endpoints translate with their block), then dv_route72c.py
re-routes everything.  Link list, link classes, widths, masters and interfaces are untouched (release freeze 10-22).

cap18 route model (dv_route72c, cap 150.9 bit/um): peak 1.184, 186 over-capacity edges.  Measured hot spots
(--dump of the cap18 route):
  H1 1.184  W mouth of the centre channel: the 172.8-um street between f_3L01 (x 7716-9153, y 16831-20503) and s_0S
            at x 9196-9283, y 16788-17433 -- every W-frame x_frame / s_0N coll / ret bundle bound for the centre channel
            climbs that street because f_3L01 sits beside the channel mouth (y 17389-17692).
  H2 1.114  HBM service row y 1353: the 86.4-um gap between stacked irg pairs (irg_01/irg_00, irg_02/irg_03,
            irg_05/irg_04, irg_06/irg_07) carries the N-face etap<->irg hbm lanes of TWO lower irgs on one line.
  H3 1.109  E SerDes column gap y 7876-7962 (lk_ES1 / lk_EN0, 86.4 um) crossed by s_4N/s_5N -> E-frame x_frame.
  H4 1.005  W SerDes column gap y 7876-7962 (lk_WS1 / lk_WN0).
  H5 1.002  129.6-um street s_1S/s_2S (wrapper W-face xc pins) -- negotiable once H1 is open.
Fix (structural; rigid re-slots into existing white space, nothing resized, no interface change):
  * f_3L01 leaves the channel mouth -> col6 row x 7716.16, y 12152.8 (old lk_WN1/lk_WN3 row): the W corridor
    between f_3L01 and the SerDes/bk_sel above it is open beside the mouth (both variants).
  * frame arrays W and E: row k of every frame column moves up k x 172.8 (row streets 86.4 -> 259.2), using the
    1.39-mm empty strip above both arrays (top passage 1392 -> 355 um).
  * col6 SerDes rows re-spaced (gaps 86.4 -> 172.8); bk_sel up 344 (top passage over it 688 -> 344).
  * HBM row: a stacked irg pair is only kept where its lanes do not pass another irg's lane row (E: irg_04 -> lower
    row, irg_06 + irg_07 -> free slot x 23083 E of the group).
  * E SerDes: lk_EN0/lk_EN1 + copy-A/B reserves up 172.8 (lk_ES1/lk_EN0 gap 86.4 -> 259.2).
VARIANTS
  main: lk_WN1 / lk_WN3 -> (8320.96 / 7716.16, 17002.4) just above the corridor (coll lanes to s_0N get SHORTER);
        bundles reach the mouth through the 400-um street x 8925-9326; W HBM: irg_00 -> free slot (8320.96, 100)
        (iqf -> (9098.56, 1396)), irg_02/irg_03 stay stacked (their lanes run E without passing another lane row).
  fb:   lk_WN1 / lk_WN3 -> the empty col6 sub-column below (8320.96, 4117.6 / 100); the whole corridor between
        f_3L01 and bk_sel is open (coll lanes to s_0N longer); W HBM: phy/ctrl/etap rows + E irgs shift E 86.4, W irgs
        irg_01+irg_00 stacked at x 8925.76 (W-most), irg_02 / irg_03 single in the lower row, iqf above irg_02.
Checks: seal, >= 86.4 between all bodies + blockages, every endpoint on its face.
Usage: g9f_cap19_plan.py PLAN OUT --variant main|fb
"""
import argparse, json
from pathlib import Path

SEAL, GAP = 100.0, 86.4
ROW_DY = 172.8   # frame-array row streets 86.4 -> 259.2 (uses the 1.39-mm empty strip above both frame arrays)

COMMON_E = {  # E SerDes column gap 86.4 -> 259.2 (with the copy-A/B reserves); E HBM irgs re-slotted
    'dy': {'lk_EN0': 172.8, 'lk_EN1': 172.8, 'link_1_4': 172.8, 'link_1_5': 172.8},
}
VARIANTS = {
    'main': {
        'abs': {'f_3L01': (7716.16, 12152.8), 'lk_WN1': (8320.96, 17002.4), 'lk_WN3': (7716.16, 17002.4),
                'bk_sel': (7716.16, 21020.0), 'lk_WS1': (7716.16, 4117.6), 'lk_WN0': (7716.16, 8134.4), 'lk_WN2': (8320.96, 8134.4),
                'irg_00': (8320.96, 100.0), 'iqf': (9098.56, 1396.0),
                'irg_04': (21959.6, 100.0), 'irg_06': (23083.2, 100.0), 'irg_07': (23083.2, 1396.0)},
        'dx': {},
    },
    'fb': {
        'abs': {'lk_WN3': (8320.96, 100.0),
                'irg_01': (8925.76, 100.0), 'irg_00': (8925.76, 1396.0), 'irg_02': (10048.96, 100.0),
                'irg_03': (11172.16, 100.0), 'iqf': (10048.96, 2150.0),
                'lk_WS1': (7716.16, 4117.6), 'lk_WN1': (8320.96, 4117.6), 'lk_WN0': (7716.16, 8134.4), 'lk_WN2': (8320.96, 8134.4),
                'f_3L01': (7716.16, 12152.8), 'bk_sel': (7716.16, 21020.0),
                'irg_05': (20922.8, 100.0), 'irg_04': (22046.0, 100.0), 'irg_06': (23169.2, 100.0), 'irg_07': (23169.2, 1396.0)},
        'dx': {**{'phy_hbm': 86.4}, **{f'ctrl_{i:02d}': 86.4 for i in range(16)}, **{f'etap_{i:02d}': 86.4 for i in range(16)}},
    },
}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('plan'); ap.add_argument('out'); ap.add_argument('--variant', choices=sorted(VARIANTS), required=True)
    v = ap.parse_args(); p = json.load(open(v.plan)); W, H = p['facts']['die_um']
    spec = VARIANTS[v.variant]
    allr = p['blocks'] + p.get('blockages', [])
    by = {b['name']: b for b in allr}
    move = {}
    for n, (x, y) in spec['abs'].items():
        move[n] = (x - by[n]['x'], y - by[n]['y'])
    for n, d in spec['dx'].items():
        move[n] = (move.get(n, (0, 0))[0] + d, move.get(n, (0, 0))[1])
    # frame arrays (W x < 7700, E x > 25300; not the col6 / E-inner frames): row k of each column up k x ROW_DY
    for side in ('W', 'E'):
        fr = [b for b in p['blocks'] if b.get('kind') == 'frame' and ((b['x'] < 7700) if side == 'W' else (b['x'] > 25300))]
        for col in sorted({round(b['x'], 1) for b in fr}):
            rows = sorted((b for b in fr if round(b['x'], 1) == col), key=lambda b: b['y'])
            for k, b in enumerate(rows):
                if k:
                    move[b['name']] = (0.0, k * ROW_DY)
    for n, d in COMMON_E['dy'].items():
        move[n] = (move.get(n, (0, 0))[0], move.get(n, (0, 0))[1] + d)
    idx = {b['name']: i for i, b in enumerate(p['blocks'])}
    rec = {}
    for n, (dx, dy) in move.items():
        b = by[n]; rec[n] = dict(before=[round(b['x'], 4), round(b['y'], 4)])
        b['x'] = round(b['x'] + dx, 4); b['y'] = round(b['y'] + dy, 4); rec[n]['after'] = [b['x'], b['y']]
        b['scope'] = (b.get('scope', '') + f' | cap19 {v.variant}: rigid move ({dx:+.2f}, {dy:+.2f}) um, body/pins unchanged').strip(' |')
    for l in p['links']:
        for e in l['e']:
            n = p['blocks'][e[0]]['name']
            if n in move:
                e[2] = round(e[2] + move[n][0], 4); e[3] = round(e[3] + move[n][1], 4)
        for k in ('h', 'sp', 's', 'L', 'station_dirs'):
            l.pop(k, None)
    # checks
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
    p['facts']['physical72']['cap19'] = dict(variant=v.variant, tool='g9f_cap19_plan.py', base='cap18 528fc3c9f plan (cap17 pool body)',
                                             moves=rec, rule='rigid re-slot into white space; no resize, no pin/face/interface change')
    p['facts']['physical72']['routing'] = 'cap19 unrouted: dv_route72c.py required'
    Path(v.out).write_text(json.dumps(p, indent=1))
    print('CAP19_PLAN', v.variant, json.dumps(rec))


if __name__ == '__main__':
    main()
