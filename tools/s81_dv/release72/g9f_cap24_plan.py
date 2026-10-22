#!/usr/bin/env python3
"""S81 DIE72 cap24 floorplan: cap19 FB re-slots + an open W street + wider centre/lower channels (STW-S81c-DIE 10-22).

Input = the output of g9f_cap19_plan.py --variant fb (cap18 plan, cap19 FB rigid re-slots: frame-array row streets,
E SerDes re-spacing, HBM row with no irg lane row crossing another, rsv rows -32.2). Every move here is RIGID (no
resize, no pin-face change: endpoints translate with their block). Links, widths, masters and interfaces are
unchanged (release freeze 10-22, STEWARD-approved cap24 scope).

Why (read-only GRT probe of cap20 FB = cap19 FB, congestion_iterations 0, 10-22 05:28): congestion is vertical-led.
  (1) W seam x 9-10.5 mm, y 11.5-17.5 mm: W-frame x_frame bundles converge on the centre-channel mouth through the
      173-um street between f_3L01 (col6, y 12.2-15.8) and s_0S; the FB position of lk_WN1/WN3 (die bottom) made
      their coll lanes to s_0N climb that same seam.
  (2) centre channel y ~17.5, x 9-12 (s_0S/s_0N gap 345 um): H, x_frame lanes of the 2x/3x W frames.
  (3) lower channel y ~10.4, x 18-23 (rsv tops / s_5..s_7 S bottoms, 139 um): H, x_frame lanes of the 4x-6x frames.
Fix:
  * col6 re-packed bottom-up: lk_WS0|lk_WS1, lk_WN0|lk_WN2, bk_sel, [open street], lk_WN3|lk_WN1, f_3L01.
    f_3L01 leaves y 10-18; the col6 street is the full col6 width (x 7716-9326, ~1.6 mm) over y 12.58-18.0 mm
    (narrower 400-700 um strips beside lk_WN0/2 and bk_sel below it). lk_WN1/WN3 sit at y 18.1-21.9, beside s_0N
    (their coll lanes stay short, unlike cap19 FB).
  * centre channel: s_0N up D_c (MAIN 172.8, FB 259.2) -> the channel along s_0 is 518 / 604 um.
  * lower channel x 12.8-22.0: rsv_04..rsv_13 down D_l more (rsv_05 and rsv_11 move together: frozen pvso ring
    ages); rsv_00..03, 14, 15 stay (W irg_00 and E irg_07 stacked rows sit under them). s_7S/s_7N up D_l over x
    20.9-23.75 (the rsv_14/15 span), so the channel grows by D_l at every x of hotspot (3).
Checks: seal, >= 86.4 between all bodies + blockages, every endpoint on its face.
Usage: g9f_cap24_plan.py CAP19_FB_PLAN OUT --variant main|fb
"""
import argparse, json
from pathlib import Path

SEAL, GAP = 100.0, 86.4
SD_H, BK_H, F01_H = 3844.8, 4536.0, 3672.0
XL, XR = 7716.16, 8320.96                       # col6 sub-columns (SerDes 518.4 wide)
Y_TOP_ROW = 18100.0                             # lk_WN3 / lk_WN1 row; f_3L01 above it
COL6 = {
    'lk_WS0': (XL, 100.0), 'lk_WS1': (XR, 100.0),
    'lk_WN0': (XL, 100.0 + SD_H + GAP), 'lk_WN2': (XR, 100.0 + SD_H + GAP),
    'bk_sel': (XL, 100.0 + 2 * (SD_H + GAP)),
    'lk_WN3': (XL, Y_TOP_ROW), 'lk_WN1': (XR, Y_TOP_ROW),
    'f_3L01': (XL, Y_TOP_ROW + SD_H + GAP),
}
VARIANTS = {'main': dict(d_c=172.8, d_l=172.8), 'fb': dict(d_c=259.2, d_l=259.2)}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('plan'); ap.add_argument('out')
    ap.add_argument('--variant', choices=sorted(VARIANTS), required=True)
    v = ap.parse_args(); p = json.load(open(v.plan)); W, H = p['facts']['die_um']
    assert p['facts']['physical72'].get('cap19', {}).get('variant') == 'fb', 'input must be the cap19 FB plan'
    spec = VARIANTS[v.variant]
    allr = p['blocks'] + p.get('blockages', [])
    by = {b['name']: b for b in allr}
    move = {n: (x - by[n]['x'], y - by[n]['y']) for n, (x, y) in COL6.items()}
    move['s_0N'] = (0.0, spec['d_c'])
    for i in range(4, 14):
        move[f'rsv_{i:02d}'] = (0.0, -spec['d_l'])
    for n in ('s_7S', 's_7N'):
        move[n] = (0.0, spec['d_l'])
    rec = {}
    for n, (dx, dy) in move.items():
        b = by[n]; rec[n] = dict(before=[round(b['x'], 4), round(b['y'], 4)])
        b['x'] = round(b['x'] + dx, 4); b['y'] = round(b['y'] + dy, 4); rec[n]['after'] = [b['x'], b['y']]
        b['scope'] = (b.get('scope', '') + f' | cap24 {v.variant}: rigid move ({dx:+.2f}, {dy:+.2f}) um, body/pins unchanged').strip(' |')
    for l in p['links']:
        for e in l['e']:
            n = p['blocks'][e[0]]['name']
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
    # the open street: no body in col6 (x 7716 .. s_0 W edge) over the street rows
    y0, y1 = COL6['bk_sel'][1] + BK_H + GAP, Y_TOP_ROW - GAP
    s0 = by['s_0S']['x']
    inside = [b['name'] for b in allr if b['x'] < s0 and b['x'] + b['w'] > XL and b['y'] < y1 and b['y'] + b['h'] > y0]
    assert not inside, inside
    p['facts']['physical72']['cap24'] = dict(variant=v.variant, tool='g9f_cap24_plan.py', base='cap19 FB plan (g9f_cap19_plan.py --variant fb)',
                                             moves=rec, w_street_um=[round(XL, 2), round(y0, 2), round(s0, 2), round(y1, 2)],
                                             centre_channel_plus_um=spec['d_c'], lower_channel_plus_um=spec['d_l'],
                                             rule='rigid re-slot into white space; no resize, no pin/face/interface change')
    p['facts']['physical72']['routing'] = 'cap24 unrouted: dv_route72c.py required'
    Path(v.out).write_text(json.dumps(p, indent=1))
    print('CAP24_PLAN', v.variant, 'street', p['facts']['physical72']['cap24']['w_street_um'], json.dumps(rec))


if __name__ == '__main__':
    main()
