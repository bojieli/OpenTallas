#!/usr/bin/env python3
"""S81 DIE72 cap26 floorplan candidates on top of cap24 (STW-S81c-DIE2-C25 10-22): rigid re-slots only.

Input = the output of g9f_cap24_plan.py (cap24 unrouted plan, MAIN or FB).  Every move is RIGID: no resize, no
mirror, no pin-face change (endpoints translate with their block); links, widths, masters and interfaces unchanged
(release freeze 10-22).

Why (cap24main read-only GRT probe, 10:12: 21.09M, W seam + lower channel gone).  Remaining classes:
 (a) (7,11)/(7,12) V: lk_WN0/WN2 coll lanes (E-face pins at y 7.8) climb ~13 mm through the ~700-um strip E of
     bk_sel to s_0N W pins at y 21.06-21.73, with x_f_0R01/0L01 and tvS_bk_sel;
 (b) centre mouth (9,17); (c) E centre channel (20,17): x_f_4R01/6R01/4R02/6R02.
Moves:
 col6 re-stacks (sub-columns XL 7716.16 / XR 8320.96; SerDes 518.4 x 3844.8, bk_sel 907.2 x 4536 at XL):
   A  WS0|WS1 100, bk_sel, WN0|WN2 right below the open street (steward candidate 1), WN3|WN1 18100, f_3L01 top
   B  WS0|WS1 100, bk_sel, open street, WN0|WN2 right under WN3|WN1 (their pins at y ~17.9 -> 3.2-3.8 mm to s_0N)
   C  bk_sel 100, WS0|WS1 at the s_0S pin height (pins 10.2 / 13.9 vs s_0S 13.7-14.15), WN0|WN2 as B
 E-centre (suffix e): s_5N and s_6N down 172.8 (centre channel x 18.1-20.7 +172.8; lower-channel gap there 311.8
   -> 139, the pre-cap24 value; rsv rows unchanged: rsv_05/11 ring ages and the dn_05_03 805-b relay limit stand).
Checks: seal, >= 86.4 between all bodies + blockages, every endpoint on its face.
Usage: g9f_cap26_plan.py CAP24_PLAN OUT --variant A|B|C|Ae|Be|Ce
"""
import argparse, json
from pathlib import Path

SEAL, GAP = 100.0, 86.4
SD_H, BK_H = 3844.8, 4536.0
XL, XR = 7716.16, 8320.96
Y_WN31 = 18100.0
Y_WN02_HI = Y_WN31 - GAP - SD_H                      # 14168.8: WN0|WN2 under WN3|WN1
LAYOUT = {
    'A': {'lk_WS0': (XL, 100.0), 'lk_WS1': (XR, 100.0), 'bk_sel': (XL, 100.0 + SD_H + GAP),
          'lk_WN0': (XL, 100.0 + SD_H + GAP + BK_H + GAP), 'lk_WN2': (XR, 100.0 + SD_H + GAP + BK_H + GAP)},
    'B': {'lk_WS0': (XL, 100.0), 'lk_WS1': (XR, 100.0), 'bk_sel': (XL, 100.0 + SD_H + GAP),
          'lk_WN0': (XL, Y_WN02_HI), 'lk_WN2': (XR, Y_WN02_HI)},
    'C': {'bk_sel': (XL, 100.0), 'lk_WS0': (XL, 10100.0), 'lk_WS1': (XR, 10100.0),
          'lk_WN0': (XL, Y_WN02_HI), 'lk_WN2': (XR, Y_WN02_HI)},
}
E_CENTRE = {'s_5N': (0.0, -172.8), 's_6N': (0.0, -172.8)}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('plan'); ap.add_argument('out')
    ap.add_argument('--variant', choices=sorted(list(LAYOUT) + [k + 'e' for k in LAYOUT]), required=True)
    v = ap.parse_args(); p = json.load(open(v.plan)); W, H = p['facts']['die_um']
    assert 'cap24' in p['facts']['physical72'], 'input must be a cap24 plan'
    allr = p['blocks'] + p.get('blockages', [])
    by = {b['name']: b for b in allr}
    assert by['lk_WN3']['y'] == Y_WN31 and by['lk_WN1']['y'] == Y_WN31
    move = {n: (x - by[n]['x'], y - by[n]['y']) for n, (x, y) in LAYOUT[v.variant[0]].items()}
    if v.variant.endswith('e'):
        move.update(E_CENTRE)
    rec = {}
    for n, (dx, dy) in move.items():
        b = by[n]; rec[n] = dict(before=[round(b['x'], 4), round(b['y'], 4)])
        b['x'] = round(b['x'] + dx, 4); b['y'] = round(b['y'] + dy, 4); rec[n]['after'] = [b['x'], b['y']]
        b['scope'] = (b.get('scope', '') + f' | cap26 {v.variant}: rigid move ({dx:+.2f}, {dy:+.2f}) um, body/pins unchanged').strip(' |')
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
    p['facts']['physical72']['cap26'] = dict(variant=v.variant, tool='g9f_cap26_plan.py', base='cap24 plan (g9f_cap24_plan.py)', moves=rec,
                                             rule='rigid re-slot into white space; no resize, no mirror, no pin/face/interface change')
    p['facts']['physical72']['routing'] = 'cap26 unrouted: dv_route72c.py required'
    Path(v.out).write_text(json.dumps(p, indent=1))
    print('CAP26_PLAN', v.variant, json.dumps(rec))


if __name__ == '__main__':
    main()
