"""Regression for kvs14p real-case MY pin-lattice failure."""

import unittest

from kv_lane_orientation import adapt, origin_rules


def macro(mixed=True):
    pins = [dict(name="ck", use="SIGNAL", rects=[("M3", (8100, 0, 8118, 37))])]
    if mixed:
        pins.append(
            dict(
                name="tie_hi", use="SIGNAL", rects=[("M5", (9216, 12876, 9240, 12960))]
            )
        )
    return dict(name="lane", W=12960, H=12960, pins=pins)


class OrientationTest(unittest.TestCase):
    def test_mixed_clock_strap_lattices_adapt_x_only(self):
        text = "ot_mts::place [$_blk findInst hop] 1 2 R180\n"
        placed, report = adapt(text, {"hop": ("lane", "")}, {"lane": macro()})
        self.assertIn("1 2 MX", placed)
        self.assertEqual(report["changes"][0]["max_pin_x_displacement_um"], 12.96)
        self.assertFalse(origin_rules(macro(), "MY")["x"]["legal_origins_mod_joint_nm"])

    def test_single_lattice_keeps_legal_mirror(self):
        text = "ot_mts::place [$_blk findInst hop] 1 2 MY\n"
        placed, report = adapt(text, {"hop": ("lane", "")}, {"lane": macro(False)})
        self.assertEqual(placed, text)
        self.assertEqual(report["changes"], [])

    def test_offtrack_mutant_refused(self):
        m = macro()
        m["pins"][0]["rects"].append(("M3", (8101, 100, 8119, 137)))
        with self.assertRaisesRegex(ValueError, "no legal orientation"):
            adapt(
                "ot_mts::place [$_blk findInst hop] 1 2 R0",
                {"hop": ("lane", "")},
                {"lane": m},
            )

    def test_missing_placement_refused(self):
        with self.assertRaisesRegex(ValueError, "placement missing"):
            adapt("", {"hop": ("lane", "")}, {"lane": macro()})


if __name__ == "__main__":
    unittest.main()


class IncidentReachTest(unittest.TestCase):
    def vehicle(self, missing=False):
        from kv_lane_reach import audit

        lef = """MACRO qkd_rlysh_1
 SIZE 12.96 BY 12.96 ;
 PIN a
 DIRECTION INPUT ;
 LAYER M4 ;
 RECT 0 1.0 0.084 1.024 ;
 END a
 PIN b
 DIRECTION OUTPUT ;
 LAYER M4 ;
 RECT 12.876 1.0 12.96 1.024 ;
 END b
END qkd_rlysh_1
"""
        if missing:
            lef = lef.replace("RECT 0 1.0 0.084 1.024 ;", "")
        netlist = """module test();
 wire [0:0] n;
 qkd_rlysh_1 source (.b(n));
 qkd_rlysh_1 target (.a(n));
endmodule
"""
        before = (
            "ot_mts::place [$_blk findInst source] 400 0 R0\n"
            "ot_mts::place [$_blk findInst target] 0 0 MY\n"
        )
        return audit(
            netlist,
            lef,
            before,
            before.replace("0 0 MY", "0 0 R0"),
            {"changes": [{"instance": "target"}]},
            [(36, 400), (296, 370), (100000, 340)],
        )

    def test_new_overreach_refuses_and_requests_station(self):
        report = self.vehicle()
        self.assertEqual(report["status"], "FAIL")
        self.assertEqual(report["summary"]["before_overreach_bits"], 0)
        self.assertEqual(report["summary"]["newly_overreach_bits"], 1)
        self.assertEqual(report["reservation_repairs"][0]["minimum_extra_hops"], 1)

    def test_missing_actual_pin_geometry_refuses(self):
        report = self.vehicle(missing=True)
        self.assertEqual(report["status"], "FAIL")
        self.assertEqual(report["summary"]["unmeasured_pairs"], 1)
