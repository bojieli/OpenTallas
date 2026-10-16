#!/usr/bin/env python3
"""redesign-ds 2026-10-09: S81 tile CLOCK-PIN RULE check (generator rule proposed to s81-gen).

Measured on the open DS rows: blocks whose ck pin sits at a corner or on a short face of a long tile carry 600-1,150 ps
of CTS insertion and lose their routes to the hold window and the IO budget (dsfd_coll_core 540 x 1360.8, ck at the
N-face middle: 1,151 ps; dsfd_selt_q 756 x 159.8, ck at the W corner: 635 ps, its g_cst hold race; selt_c 129.6 x 319.7
with ck near its middle: 326 ps).  Rule: for a tile whose longer side L >= MIN_L um, the ck pin is on a LONG face
(length L) and within the middle third of that face (|pos - L/2| <= L/6), so the clock root reaches the tile centre
over at most the short dimension / 2 + L/6.  Tiles below MIN_L are exempt.

    ck_pin_rule.py [--ports physical/s81_ph_views/ports] [--die DIR ...] [--min-l 300] [--json OUT]
Prints one line per violating (die, master) with the distance from the pin to the tile centre and the suggested pin
(middle of the long face that has the most free track around it is the die generator's choice; we print the W/S
candidates)."""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def check(rec, min_l):
    w, h = rec['w_um'], rec['h_um']
    ck = None
    for k in ('ck', 'clk', 'core_clk'):
        if k in rec['ports']:
            ck = rec['ports'][k]['pins'][0]
            break
    if ck is None:
        return None
    _, ly, x0, y0, x1, y1 = ck
    x, y = (x0 + x1) / 2, (y0 + y1) / 2
    L = max(w, h)
    if L < min_l:
        return dict(ok=True, exempt=True)
    if x < 1 or x > w - 1:
        face, pos, flen = ('W' if x < 1 else 'E'), y, h
    else:
        face, pos, flen = ('S' if y < 1 else 'N'), x, w
    long_face = abs(flen - L) < 1e-6
    ok = long_face and abs(pos - flen / 2) <= L / 6
    dist = abs(x - w / 2) + abs(y - h / 2)
    best = (min(w, h) / 2) + 0.0
    return dict(ok=ok, exempt=False, face=face, pos=round(pos, 3), face_len=flen, long_face=long_face, w=w, h=h,
                ck_to_centre_um=round(dist, 1), rule_bound_um=round(best + L / 6, 1),
                suggest=('W/E mid-height y=%.1f' % (h / 2)) if h >= w else ('S/N mid x=%.1f' % (w / 2)))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--ports', default=str(ROOT / 'physical/s81_ph_views/ports'))
    ap.add_argument('--die', action='append', default=[])
    ap.add_argument('--min-l', type=float, default=300.0)
    ap.add_argument('--json')
    a = ap.parse_args()
    root = Path(a.ports)
    dies = a.die or sorted(p.name for p in root.iterdir() if p.is_dir())
    out, nbad = [], 0
    for die in dies:
        for pj in sorted((root / die).glob('*/ports.json')):
            rec = json.loads(pj.read_text())
            r = check(rec, a.min_l)
            if r is None or r.get('exempt'):
                continue
            r.update(die=die, master=rec['master'])
            out.append(r)
            if not r['ok']:
                nbad += 1
                print(f"VIOLATION {die:28} {rec['master']:28} {r['w']:7.1f} x {r['h']:7.1f}  ck {r['face']} @ {r['pos']:7.1f} "
                      f"(long face: {r['long_face']})  ck->centre {r['ck_to_centre_um']:6.1f} um (rule <= {r['rule_bound_um']})  -> {r['suggest']}")
    print(f'checked {len(out)} tiles >= {a.min_l} um, {nbad} violations')
    if a.json:
        Path(a.json).write_text(json.dumps(out, indent=1) + '\n')


if __name__ == '__main__':
    main()
