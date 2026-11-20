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

    # CLKSITE-PGCUT-1119
    def test_pg_cut_windows_strap_layers_only(self):
        P = FakeP([{"rect_um": [1, 1, 2, 2], "kind": "die_clock_tree", "route_layers": "M1-M4"},
                   {"rect_um": [3, 3, 4, 4], "kind": "die_clock_tree", "route_layers": "M5-M7", "edge_pad_sites": 0},
                   {"rect_um": [5, 5, 6, 6], "kind": "die_clock_tree", "route_layers": "M1-M7"},
                   {"rect_um": [7, 7, 8, 8], "kind": "die_clock_tree", "route_layers": "M1-M2"},
                   {"rect_um": [9, 9, 10, 10], "kind": "die_clock_tree", "route_layers": "M1-M7", "pg_cut": False},
                   {"rect_um": [11, 11, 12, 12], "kind": "die_clock_tree"},
                   {"rect_um": [13, 13, 14, 14], "kind": "landing_ring_bank", "route_layers": "M1-M7"}])
        self.assertEqual(gen_phys.reserved_pg_cut_windows(P, "t"),
                         [((1.0, 1.0, 2.0, 2.0), [3, 4]), ((3.0, 3.0, 4.0, 4.0), [5, 6, 7]),
                          ((5.0, 5.0, 6.0, 6.0), [3, 4, 5, 6, 7])])
        self.assertEqual(gen_phys.reserved_pg_cut_windows(FakeP([{"rect_um": [1, 1, 2, 2], "kind": "die_clock_tree"}]), "t"), [])

    def test_pg_cut_tcl_rows_and_rails_kept(self):
        tcl = gen_phys.reserved_pg_cut_tcl([((3.752, 648.54, 5.428, 648.81), [5, 6, 7])])
        self.assertIn("{3.752 648.54 5.428 648.81 {5 6 7}}", tcl)
        self.assertIn("if {$L < 3} continue", tcl)          # M1/M2 followpin rails never cut
        self.assertIn("if {$bot < 2} continue", tcl)        # M1-M2 rail vias kept
        self.assertTrue(tcl.startswith("# GENERATED") and "uplevel #0 {" in tcl)
        self.assertEqual(tcl.count("{"), tcl.count("}"))

    def test_pg_cut_rail_keeper(self):
        """COORD 11-19: hd_mesh lost the last stack via of 14 rail segments (28 rows) to an M1-M7 site; the cut records what
        it removes and rebuilds the stack on a same-net bypass beside the site, reporting what it cannot place."""
        tcl = gen_phys.reserved_pg_cut_tcl([((228.744, 501.66, 230.904, 502.74), [3, 4, 5, 6, 7])])
        self.assertIn("lappend kc_rm [list $net $sw [$s isVia]", tcl)        # removed vias/fill recorded before destroy
        self.assertIn("proc kc_orphans", tcl)
        self.assertIn("foreach l $kc_strap_lv { if {$l >= 3} { lappend kc_slv $l } }", tcl)   # bypass on the lowest strap layer
        self.assertIn("odb::dbSBox_create $sw0 $kc_l5 $a $b $c $d STRIPE", tcl)
        self.assertIn("orphan_rails_left=$kc_orph_left", tcl)
        self.assertEqual(tcl.count("{"), tcl.count("}"))
        self.assertNotIn("%", tcl.replace("%d", ""))                           # every format slot filled

    # CLKSITE-TAP-ESCAPE-1117
    def test_tap_escape_pieces(self):
        site = (1361.56, 117.72, 1365.34, 119.34)                       # sd9f clk_t8 site + pin
        pin = (1362.64, 117.92, 1362.672, 118.688)
        pieces, k = gen_phys.tap_escape_pieces(site, [pin, (10, 10, 11, 11)])
        self.assertEqual(k, 1)
        self.assertEqual(len(pieces), 2)
        self.assertAlmostEqual(pieces[0][2], 1362.54); self.assertAlmostEqual(pieces[1][0], 1362.772)
        self.assertEqual((pieces[0][1], pieces[0][3], pieces[1][1], pieces[1][3]), (117.72, 119.34, 117.72, 119.34))
        self.assertEqual(gen_phys.tap_escape_pieces(site, [(10, 10, 11, 11)]), ([site], 0))
        # pin at the site edge: one piece; two pins closer than 2 x clear: one merged column
        self.assertEqual(len(gen_phys.tap_escape_pieces((0, 0, 4, 2), [(0.05, 0.5, 0.082, 1.2)])[0]), 1)
        p2, k2 = gen_phys.tap_escape_pieces((0, 0, 4, 2), [(1.0, 0.5, 1.032, 1.2), (1.15, 0.5, 1.182, 1.2)])
        self.assertEqual((len(p2), k2), (2, 1))

    def test_route_obstruction_escape_only_on_pin_layer(self):
        site = (10.0, 10.0, 14.0, 12.0)
        pins = {"M7": [(11.0, 10.5, 11.032, 11.268)]}
        L = gen_phys.route_obstruction_lines([(site, ["M6", "M7"])], pins)
        self.assertEqual(sum("findLayer M6" in l for l in L), 1)
        self.assertEqual(sum("findLayer M7" in l for l in L), 2)
        self.assertIn('puts "OT_RESERVED_SITES route_obstructions=3"', L)
        self.assertTrue(any("tap_escape_columns=1" in l for l in L))
        # no pin on the site / escape off / legacy 2-tuple item: bytes of the old emitter
        old = gen_phys.route_obstruction_lines([(site, ["M6", "M7"])])
        self.assertEqual(gen_phys.route_obstruction_lines([(site, ["M6", "M7"], False)], pins), old)
        self.assertEqual(gen_phys.route_obstruction_lines([(site, ["M6", "M7"], True)], {"M7": [(1, 1, 2, 2)]}), old)
        self.assertEqual(len(old), 3)

    def test_edge_pad_is_placement_only(self):
        tap = [("clk_t1", 12.0, 11.0)]
        orig = gen_phys.interior_tap_pin_rects
        gen_phys.interior_tap_pin_rects = lambda P, tn: {"M7": [(11.984, 10.616, 12.016, 11.384)]}
        try:
            P = FakeP([{"rect_um": [10, 10, 20, 12], "kind": "die_clock_tree", "route_layers": "M1-M7"}])
            pre, _, _ = gen_phys.reserved_sites_tcl(P, "t")
            self.assertIn("dbBlockage_create $rs_b [expr {round(9.838*$rs_u)}] [expr {round(10*$rs_u)}] [expr {round(20.162*$rs_u)}]", pre)
            self.assertIn("findLayer M1] [expr {round(10*$rs_u)}] [expr {round(10*$rs_u)}] [expr {round(20*$rs_u)}]", pre)
            self.assertEqual(pre.count("findLayer M7"), 2)            # escape column over the tap pin
            self.assertEqual(pre.count("dbObstruction_create"), 8)
            P0 = FakeP([{"rect_um": [10, 10, 20, 12], "kind": "die_clock_tree", "route_layers": "M1-M7",
                         "edge_pad_sites": 0, "tap_escape": False}])
            pre0, _, _ = gen_phys.reserved_sites_tcl(P0, "t")
            self.assertEqual(pre0.count("dbObstruction_create"), 7)
            self.assertIn("dbBlockage_create $rs_b [expr {round(10*$rs_u)}]", pre0)
            self.assertNotIn("edge_pad_sites", pre0)
        finally:
            gen_phys.interior_tap_pin_rects = orig


if __name__ == "__main__":
    unittest.main()
