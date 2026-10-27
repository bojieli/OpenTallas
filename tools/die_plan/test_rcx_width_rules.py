#!/usr/bin/env python3
"""CLOCK-128-R6: width-characterised OpenRCX rules + opt-in extraction in clock_routed (unit tests, no OpenROAD)."""
import importlib.util
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import clock_routed as CR  # noqa: E402
import rcx_width_rules as RW  # noqa: E402

MINI = """Extraction Rules for OpenRCX

Metal 8 RESOVER
WIDTH Table 1 entries:  0.04

Metal 8 RESOVER 0
DIST count 2 width 0.04
0 0 0 0.00844656
0 0.04 0 0.00844656
END DIST

Metal 8 RESOVER 1
DIST count 0 width 0.04
END DIST

Metal 8 DIAGUNDER
WIDTH Table 1 entries:  0.04

Metal 8 DIAGUNDER 9
DIST count 1 width 0.04
0 0 3.54516e-05 0.00422328
END DIST

Metal 9 UNDER
WIDTH Table 0 entries:

Metal 9 UNDER 10

Metal 3 RESOVER
WIDTH Table 1 entries:  0.018

Metal 3 RESOVER 0
DIST count 1 width 0.018
0 0 0 0.031287
END DIST
"""


class RulesTest(unittest.TestCase):
    def test_rpersq_is_table_r_times_width(self):
        r = RW.rpersq(MINI)
        self.assertAlmostEqual(r["M8"], 8.44656 * 0.04, places=6)
        self.assertAlmostEqual(r["M3"], 31.287 * 0.018, places=6)

    def test_widen_keeps_w0_rows_and_scales_r(self):
        txt, prov = RW.widen(MINI, cal={}, widths=[0.16])
        L = txt.split("\n")
        self.assertIn("WIDTH Table 2 entries:  0.04 0.16", L)
        # original 0.04 block untouched, a 0.16 block follows with R x 0.25
        i = L.index("Metal 8 RESOVER 0")
        self.assertEqual(L[i + 1:i + 5], MINI.split("\n")[MINI.split("\n").index("Metal 8 RESOVER 0") + 1:][:4])
        j = L.index("DIST count 2 width 0.16")
        self.assertAlmostEqual(float(L[j + 1].split()[-1]), 0.00844656 / 4, places=9)
        # DIAGUNDER copied (C unchanged), R scaled; empty tables and other layers untouched
        k = L.index("Metal 8 DIAGUNDER 9")
        self.assertEqual(L[k + 4], "DIST count 1 width 0.16")
        v = [float(x) for x in L[k + 5].split()]
        self.assertAlmostEqual(v[2], 3.54516e-05)
        self.assertAlmostEqual(v[3], 0.00422328 / 4, places=9)
        self.assertTrue(any(x.startswith("WIDTH Table 0 entries:") for x in L))
        self.assertEqual(L.count("WIDTH Table 1 entries:  0.018"), 1)

    def test_shipped_rules_have_016_entry_and_provenance(self):
        p = HERE / "rcx" / "asap7_rcx_ndr016.rules"
        t = p.read_text()
        # M8 RESOVER/OVER/UNDER/DIAGUNDER/OVERUNDER + M9 RESOVER/OVER/OVERUNDER (M9 UNDER/DIAGUNDER are empty)
        self.assertEqual(t.count("WIDTH Table 2 entries:  0.04 0.16"), 8)
        self.assertTrue((HERE / "rcx" / "asap7_rcx_ndr016.rules.provenance.json").exists())
        r = RW.rpersq(t)
        self.assertEqual(sorted(r), [f"M{i}" for i in range(1, 10)])


class RouteTclTest(unittest.TestCase):
    def test_stock_default_unchanged(self):
        self.assertEqual(CR.rcx_tcl(), f"extract_parasitics -ext_model_file {CR.STOCK_RULES}")
        self.assertIn("@RCX@", CR.ROUTE_TCL)

    def test_ndr_sets_every_layer_and_lef_res(self):
        t = CR.rcx_tcl("ndr", MINI)
        self.assertIn("[$ot_tech findLayer M8] setResistance 0.337862", t)
        self.assertIn("-ext_model_file /out/rcx_ndr.rules -lef_res", t)


@unittest.skipUnless(importlib.util.find_spec("scipy"), "scipy not installed")
class SolverTest(unittest.TestCase):
    def test_parallel_plate_limit(self):
        import fd2d
        cc, fr = fd2d.pattern(4.0, 0.08, 1.0, below=0.1, neighbours=False, eps_r=1.0, xspan=6)
        area = fd2d.EPS0 * 4.0 / 0.1
        self.assertGreater(2 * fr, area)            # area + fringe
        self.assertLess(2 * fr, area * 1.15)


if __name__ == "__main__":
    unittest.main()
