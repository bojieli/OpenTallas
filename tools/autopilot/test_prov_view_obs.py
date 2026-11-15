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



class ContractObsTop(unittest.TestCase):
    """PROV-OBS-M5 (11-05): default OBS top M5 = PG pin layer, so core_pg_connect M5->M6 lands (no PDN-0006)"""

    def test_default_m5(self):
        self.assertEqual(P.contract_obs_top({}), 5)
        self.assertEqual(P.contract_obs_top({"obs_max": None}), 5)

    def test_plan_override(self):
        self.assertEqual(P.contract_obs_top({"obs_max": "M6"}), 6)
        self.assertEqual(P.contract_obs_top({"obs_max": "m7"}), 7)

    def test_default_lef_pg_on_top_obs_layer(self):
        with tempfile.TemporaryDirectory() as d:
            f = os.path.join(d, "m.lef")
            pins = [dict(name="a", x=0.1, y=5.0, layer="M4")]
            open(f, "w").write(P.contract_lef("m", 20.0, 10.0, pins, {"a": "INPUT"}, P.contract_obs_top({})))
            txt = open(f).read()
            obs = txt.split("  OBS")[1]
            self.assertNotIn("LAYER M6", obs)
            self.assertNotIn("LAYER M7", obs)
            vdd = txt.split("PIN VDD")[1].split("END VDD")[0]
            self.assertIn("LAYER M5", vdd)

if __name__ == "__main__":
    unittest.main()
