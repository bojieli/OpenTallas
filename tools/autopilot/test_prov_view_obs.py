#!/usr/bin/env python3
"""Contract LEF OBS: blanket except pin windows on the pin layer and the layer above (DRT-0073 class, 11-05)."""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import prov_view as P


def rects(lines):
    cur, out = None, {}
    for ln in lines:
        s = ln.split()
        if s[0] == "LAYER":
            cur = s[1]
            out[cur] = []
        else:
            out[cur].append(tuple(float(v) for v in s[1:5]))
    return out


def covered(rs, x, y):
    return any(a <= x <= c and b <= y <= d for a, b, c, d in rs)


class ContractObs(unittest.TestCase):
    W, H = 100.0, 50.0
    PINS = [dict(name="a", x=99.9, y=20.0, layer="M4"), dict(name="b", x=0.1, y=30.0, layer="M4"),
            dict(name="c", x=40.0, y=49.9, layer="M5")]

    def setUp(self):
        self.o = rects(P.contract_obs(self.W, self.H, self.PINS, 7))

    def test_below_pin_layer_blanket(self):
        for lay in ("M1", "M2", "M3"):
            self.assertEqual(self.o[lay], [(0.0, 0.0, self.W, self.H)])

    def test_pin_layer_open(self):
        self.assertFalse(covered(self.o["M4"], 99.9, 20.0))
        self.assertFalse(covered(self.o["M4"], 0.1, 30.0))
        self.assertFalse(covered(self.o["M5"], 99.9, 20.0), "via up from M4")
        self.assertFalse(covered(self.o["M5"], 40.0, 49.9))
        self.assertFalse(covered(self.o["M6"], 40.0, 49.9), "via up from M5")

    def test_rest_stays_blocked(self):
        self.assertEqual(self.o["M7"], [(0.0, 0.0, self.W, self.H)])
        self.assertTrue(covered(self.o["M6"], 99.9, 20.0), "M4 pin does not open M6")
        for x, y in ((50.0, 25.0), (99.9, 21.0), (0.1, 10.0), (20.0, 0.1), (60.0, 49.9)):
            self.assertTrue(covered(self.o["M4"], x, y), (x, y))

    def test_lef_info_top_unchanged(self):
        with tempfile.TemporaryDirectory() as d:
            f = os.path.join(d, "m.lef")
            dirs = {"a": "INPUT", "b": "INPUT", "c": "OUTPUT"}
            open(f, "w").write(P.contract_lef("m", self.W, self.H, self.PINS, dirs, 7))
            self.assertEqual(P.lef_info(f)[3], 7)


if __name__ == "__main__":
    unittest.main()
