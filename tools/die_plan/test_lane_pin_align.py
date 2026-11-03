#!/usr/bin/env python3
"""lane_pin_align.py: lane mode packs each lane under its macro column, on track, no overlap, fixed pins kept;
spread mode keeps the order and spreads over the face."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lane_pin_align as LPA  # noqa: E402

W, H = 120.0, 100.0


def mk():
    pins = [dict(name='clk', layer='M5', x=2.52, y=0.24, w=0.048, h=0.48), dict(name='fault', layer='M4', x=119.9, y=50.0)]
    x = 5.0
    for kind in ('a', 'd'):                      # grouped BY KIND (the defect)
        for k in range(3):
            for b in range(8):
                pins.append(dict(name='l%02d_%s[%d]' % (k, kind, b), layer='M5', x=round(x, 3), y=0.096))
                x += 0.192
    macros = [dict(name='u.g_bank[%d].m' % k, rect_um=[10 + 35 * k, 20, 40 + 35 * k, 60]) for k in range(3)]
    return pins, macros


class T(unittest.TestCase):
    def test_lane(self):
        pins, macros = mk()
        out, led = LPA.plan(pins, macros, W, H, keep=('clk', 'fault'))
        self.assertEqual(sorted(p['name'] for p in out), sorted(p['name'] for p in pins))
        byn = {p['name']: p for p in out}
        self.assertEqual(byn['clk'], pins[0]); self.assertEqual(byn['fault'], pins[1])
        xs = sorted(p['x'] for p in out if p['layer'] == 'M5')
        self.assertTrue(all(b - a >= 0.192 - 1e-6 for a, b in zip(xs, xs[1:])))
        self.assertTrue(all(abs((x - 0.024) / 0.048 - round((x - 0.024) / 0.048)) < 1e-6 for x in xs))
        for k in range(3):   # every lane's pins sit inside a window around its own column, all kinds together
            lx = [byn['l%02d_%s[%d]' % (k, kd, b)]['x'] for kd in 'ad' for b in range(8)]
            c = 25 + 35 * k
            self.assertLess(max(abs(v - c) for v in lx), 15.0)

    def test_spread(self):
        pins = [dict(name='k[%d]' % i, layer='M4', x=0.096, y=1.0 + 0.096 * i) for i in range(200)]
        pins.append(dict(name='clk', layer='M5', x=60.0, y=50.0))
        out, rep = LPA.spread(pins, W, H, face='W', layer='M4')
        ys = [p['y'] for p in out if p['name'] != 'clk']
        self.assertEqual(ys, sorted(ys))
        self.assertGreater(ys[-1] - ys[0], 90.0)
        self.assertEqual(out[-1], pins[-1])


if __name__ == '__main__':
    unittest.main()
