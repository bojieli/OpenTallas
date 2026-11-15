import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import gen_phys, die_trial, abstract_cutout


class FakeP:
    def __init__(self, rows):
        self.types = {"t": {"outline_um": [100.0, 100.0], "clock": {"reserved_sites_um": rows}}}


LEF = """MACRO m
  PIN VDD
    USE POWER ;
    PORT
      LAYER M7 ;
        RECT 0 0 1 100 ;
    END
  END VDD
  OBS
    LAYER M1 ;
      RECT 0 0 100 100 ;
    LAYER M5 ;
      RECT 0 0 100 100 ;
  END
END m
"""


class T(unittest.TestCase):
    def test_route_obstructions_opt_in(self):
        P = FakeP([{"rect_um": [10, 10, 20, 12], "kind": "die_clock_tree", "route_layers": "M1-M7"}])
        pre, _, _ = gen_phys.reserved_sites_tcl(P, "t")
        self.assertEqual(pre.count("dbObstruction_create"), 7)
        self.assertIn("findLayer M7", pre)
        P2 = FakeP([{"rect_um": [10, 10, 20, 12], "kind": "die_clock_tree"}])
        pre2, _, _ = gen_phys.reserved_sites_tcl(P2, "t")
        self.assertNotIn("dbObstruction_create", pre2)      # default: kit bytes unchanged

    def test_windows_only_with_route_layers(self):
        P = FakeP([{"rect_um": [1, 1, 2, 2], "kind": "die_clock_tree"},
                   {"rect_um": [3, 3, 4, 4], "kind": "die_clock_tree", "route_layers": "M1-M7"},
                   {"rect_um": [5, 5, 6, 6], "kind": "landing_ring_bank", "route_layers": "M1-M7"}])
        self.assertEqual(die_trial.reserved_windows(P, "t"), [(3, 3, 4, 4)])

    def test_closed_view_cut_m1_m7_only(self):
        txt, st = abstract_cutout.cut_lef_text(LEF, [(10, 10, 20, 20)])
        self.assertEqual(st["obs_rects_in"], 2)          # M1 cut, M5 cut (M1-M7), pins untouched
        self.assertGreater(st["obs_rects_out"], 2)
        self.assertIn("RECT 0.0000 0.0000 1.0000 100.0000", txt)


if __name__ == "__main__":
    unittest.main()
