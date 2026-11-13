#!/usr/bin/env python3
"""QC-SU-LPAD-1 11-13: receiver lane pad vs kit core pin-face chains (native_istations.annotate_kit_dest).

Reproduces the QC s28 ev2st LANE_ASBUILT class (60 lanes, +2/+3/+4): sl_E3_su_c__x_su_c_su_l0_p1 table 7 = 2 boundary
flops + 2 clock landing + 3 stations of a core pin-face chain at the su_l0 receiver (internal_stations rows with
'core').  Before the fix the bind padded u_lpad D3 AND the kit built the 3-stage core chain: delivered 10."""
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import bind  # noqa: E402
import lane_asbuilt_latency as LAL  # noqa: E402
import native_istations  # noqa: E402


def fixture(cycles=7, regs=3, fixed=3, core=True, landing=2, src_regs=0, src_fixed=None):
    rows = [dict(conn="bus:x_su_c_p1_i", regs_um=[[100.0 * k, 0.0] for k in range(regs)], bit_route="per_bit",
                 leaf_um=[0.0, 0.0], core=["u_lane0", "u_lane1"], core_bits=[0, 1])] if regs else []
    if not core:
        for r in rows:
            r.pop("core"); r.pop("core_bits")
    src = {"module": "s", "buses": [{"name": "x_su_l0_p1_o", "dir": "out", "width": 8}],
           "internal_stations": [{"conn": "bus:x_su_l0_p1_o", "regs_um": [[k, 0] for k in range(src_regs)],
                                  "bit_route": "per_bit"}] if src_regs else []}
    rx = {"module": "r", "buses": [{"name": "x_su_c_p1_i", "dir": "in", "width": 8}], "internal_stations": rows,
          "hard_cores": [{"inst": "u_lane0"}, {"inst": "u_lane1"}]}
    L = {"lane": "sl_E3_su_c__x_su_c_su_l0_p1", "oname": "x_su_l0_p1_o", "iname": "x_su_c_p1_i", "src": "p", "dst": "q",
         "cycles": cycles, "ft": [], "width": 8, "clock_landing_cycles": landing}
    b = SimpleNamespace(ab={"kit_source_station_pricing": True}, types={"src": src, "rx": rx},
                        parts={"p": {"type": "src"}, "q": {"type": "rx"}}, by_type={"src": ["p"], "rx": ["q"]},
                        out_bus={"p": [L], "q": []}, in_bus={"q": [L], "p": []},
                        plan={"lanes": [{"id": L["lane"], "fixed_cycles": fixed if src_fixed is None else src_fixed}]},
                        errors=[])
    return b, L


def annotate(b):
    native_istations.annotate(b)
    native_istations.annotate_kit(b)
    native_istations.annotate_kit_dest(b)


class ReceiverCoreChain(unittest.TestCase):
    def test_su_l0_p1_reproduction(self):
        b, L = fixture()
        self.assertEqual(bind.lane_pad(L), 3)                 # the pre-fix pad: u_lpad D3 on top of the 3-stage chain
        annotate(b)
        self.assertEqual(b.errors, [])
        self.assertEqual(L["internal_kit_dest_core_cycles"], 3)
        self.assertEqual(bind.lane_pad(L), 0)                 # D0: no u_lpad, the kit core chain carries the stations
        self.assertEqual(2 + L["clock_landing_cycles"] + bind.lane_pad(L) + L["internal_kit_dest_core_cycles"], 7)

    def test_su_l1_depths(self):
        for regs, table in ((4, 8), (2, 6)):                  # su_l1 x_su_c_i / flt_su_c_i +4, x_su_c_p1_i +2
            b, L = fixture(cycles=table, regs=regs, fixed=regs)
            annotate(b)
            self.assertEqual((L["internal_kit_dest_core_cycles"], bind.lane_pad(L)), (regs, 0))

    def test_as_built_counter_agrees(self):
        """LATCHECK-1's receiver count on the fixed bound module (no u_lpad): face + core chain == the table share."""
        b, L = fixture()
        annotate(b)
        ix = LAL.ModuleIndex("    ot_dp_st #(.W(8)) u_bin_x_su_c_p1_i (.clk(clk));\n")
        st, det, prob = LAL.side_stages(ix, b.types["rx"], "x_su_c_p1_i", "in", False)
        self.assertEqual(prob, [])
        self.assertEqual((det["lpad"], det["core_chain"], st), (0, 3, 4))
        self.assertEqual(1 + L["clock_landing_cycles"] + st, L["cycles"])          # src face 1 + landing 2 + 4
        pre = LAL.ModuleIndex("    ot_dp_st #(.W(8)) u_bin_x_su_c_p1_i (.clk(clk));\n"
                              "    ot_dp_dly #(.W(9), .D(3)) u_lpad_x_su_c_p1_i (.clk(clk));\n")
        st0, det0, _ = LAL.side_stages(pre, b.types["rx"], "x_su_c_p1_i", "in", False)
        self.assertEqual(1 + 2 + st0 - L["cycles"], 3)        # the pre-fix +3 LANE_ASBUILT

    def test_plain_in_stations_stay_in_pad(self):
        b, L = fixture(core=False)                            # packed_input_delay absorbs plain IN stations
        annotate(b)
        self.assertNotIn("internal_kit_dest_core_cycles", L)
        self.assertEqual(bind.lane_pad(L), 3)

    def test_unpriced_chain_keeps_pad(self):
        b, L = fixture(fixed=0)
        annotate(b)
        self.assertNotIn("internal_kit_dest_core_cycles", L)
        self.assertEqual(bind.lane_pad(L), 3)

    def test_table_too_short_fails_closed(self):
        b, L = fixture(cycles=6)
        annotate(b)
        self.assertNotIn("internal_kit_dest_core_cycles", L)
        self.assertEqual(len(b.errors), 1)
        self.assertIn("KIT_ISTATION_LATENCY sl_E3_su_c__x_su_c_su_l0_p1", b.errors[0])

    def test_with_kit_source_stations(self):
        b, L = fixture(cycles=9, src_regs=2, src_fixed=5)     # 2 + landing 2 + src 2 + dst core 3 = 9
        annotate(b)
        self.assertEqual((L["internal_kit_source_cycles"], L["internal_kit_dest_core_cycles"], bind.lane_pad(L)), (2, 3, 0))

    def test_spine_and_no_lane_untouched(self):
        for k, v in (("spine", True), ("lane", None)):
            b, L = fixture()
            L[k] = v
            native_istations.annotate_kit_dest(b)
            self.assertNotIn("internal_kit_dest_core_cycles", L)


if __name__ == "__main__":
    unittest.main()
