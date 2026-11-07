import unittest
from types import SimpleNamespace
from unittest.mock import patch
import kit_core_clocks as K
import gen_phys as G

SOURCE = """module top (
    input wire clk,
    input wire d,
    output wire q
);
    child #(.MIF(0)) u_leaf (
        .ck(clk),
        .d(d),
        .q(q)
    );
endmodule
"""

NATIVE = """module cb (
    input wire clk,
    input wire d
);
    qfd_tile_nk_rp2_romleaf_rr u_u_t_2_2 (
        .ck(clk),
        .ck_lu_b0_c5(clk),
        .ck_xu(clk),
        .d(d)
    );
endmodule
"""


class NativeCoreSwapTest(unittest.TestCase):
    CORE = [dict(inst="u_t22", module="qfd_tile_nk_a0c")]

    def test_native_leaf_becomes_planned_core(self):
        text, receipt = K.swap_native_cores(NATIVE, self.CORE)
        self.assertIn("qfd_tile_nk_a0c u_t22 (", text)
        self.assertNotIn("u_u_t_2_2", text)
        self.assertNotIn(".ck_", text)
        self.assertIn(".ck(clk)", text)
        self.assertIn(".d(d)", text)
        self.assertEqual(receipt[0]["clock_entries_merged"], 3)
        # the swapped text then takes the normal core clock wiring
        wired, _ = K.wire(text, "cb", [("clk_c0", "u_t22", "ck", 0, 250)])
        self.assertIn(".ck(clk_c0)", wired)

    def test_other_cores_untouched(self):
        hard = [dict(inst="u_lane0", module="x"), dict(inst="u_t22", module="other")]
        self.assertEqual(K.swap_native_cores(NATIVE, hard), (NATIVE, []))

    def test_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "expected one native leaf"):
            K.swap_native_cores(NATIVE.replace("u_u_t_2_2", "u_u_t_2_3"), self.CORE)
        with self.assertRaisesRegex(ValueError, "expected qfd_tile_nk_rp2_romleaf_rr"):
            K.swap_native_cores(NATIVE.replace("qfd_tile_nk_rp2_romleaf_rr", "qfd_tile_other"), self.CORE)
        with self.assertRaisesRegex(ValueError, "not one net"):
            K.swap_native_cores(NATIVE.replace(".ck_xu(clk)", ".ck_xu(clk2)"), self.CORE)


class CoreClockKitTest(unittest.TestCase):
    def test_real_consumer_and_idempotence(self):
        rows = [("clk_c0", "u_bound.u_leaf", "ck", 12.5, 250)]
        text, receipt = K.wire(SOURCE, "top", rows)
        self.assertIn(".ck(clk_c0)", text)
        self.assertEqual(text.count("input wire clk_c0,"), 1)
        self.assertEqual(receipt[0]["previous_net"], "clk")
        again, _ = K.wire(text, "top", rows)
        self.assertEqual(again, text)

    def test_existing_inline_group_instance(self):
        source = SOURCE.replace("child #(.MIF(0)) u_leaf (\n        .ck(clk),\n        .d(d),\n        .q(q)\n    );",
                                "child leaf (.ck(clk), .d(d), .q(q));")
        text, rows = K.wire(source, "top", [("clk_c0", "leaf", "ck", 0, 250)])
        self.assertIn("child leaf (.ck(clk_c0)", text)
        self.assertEqual(rows[0]["instance"], "leaf")

    def test_missing_or_duplicate_consumer_fails(self):
        with self.assertRaisesRegex(ValueError, "expected one bound leaf"):
            K.wire(SOURCE, "top", [("clk_c0", "missing", "ck", 0, 250)])
        row = ("clk_c0", "u_bound.u_leaf", "ck", 0, 250)
        with self.assertRaisesRegex(ValueError, "duplicate consumer"):
            K.wire(SOURCE, "top", [row, row])

    def test_nested_leaf_keeps_bind_connection(self):
        # NESTED_LEAF_1101: S81 core clocks that reach a leaf inside a bound child keep the bind's connection
        for inst in ("u_r2.u_e10", "u_bound.u_lf.u_ve.u_m", "lf.ve.m"):
            text, receipt = K.wire(SOURCE, "top", [("clk_c0", inst, "clk", 0, 250)])
            self.assertEqual(text, SOURCE)
            self.assertEqual(receipt[0]["mode"], "physical_tap")
            self.assertFalse(K.rtl_wired(receipt))

    def test_star_tap_keeps_bind_connection(self):
        # LP_STAR_1104: `<inst>` with no pin is a legal plan tap: core_tap_rows gives "*", clock_taps.tcl hangs every pin
        for inst in ("u_bound.u_leaf", "u_leaf", "u_bound.u_lf.u_m"):
            text, receipt = K.wire(SOURCE, "top", [("clk_c0", inst, "*", 0, 250)])
            self.assertEqual(text, SOURCE)
            self.assertEqual((receipt[0]["mode"], receipt[0]["pin"]), ("physical_tap", "*"))
            self.assertFalse(K.rtl_wired(receipt))

    def test_star_mixed_with_explicit_pin_of_another_leaf(self):
        rows = [("clk_c0", "u_bound.u_ln0", "*", 0, 250), ("clk_c1", "u_bound.u_leaf", "ck", 0, 250)]
        text, receipt = K.wire(SOURCE, "top", rows)
        self.assertIn(".ck(clk_c1)", text)
        self.assertNotIn("clk_c0", text)
        self.assertEqual([r["mode"] for r in receipt], ["physical_tap", "rtl"])

    def test_mixed_nested_and_direct(self):
        rows = [("clk_c0", "u_bound.u_leaf", "ck", 0, 250), ("clk_c1", "u_r2.u_e10", "clk", 0, 250)]
        text, receipt = K.wire(SOURCE, "top", rows)
        self.assertIn(".ck(clk_c0)", text)
        self.assertNotIn("clk_c1", text)
        self.assertEqual([r["mode"] for r in receipt], ["rtl", "physical_tap"])
        self.assertTrue(K.rtl_wired(receipt))

    def test_one_bit_bus_pin_takes_base_connection(self):
        # BIT0_PIN_1106: plan/LEF pin s1__clk[0], RTL connects .s1__clk(clk) (one-bit bus) -> the base connection is rewired
        src = SOURCE.replace(".ck(clk)", ".s1__clk(clk)")
        text, receipt = K.wire(src, "top", [("clk_c0", "u_bound.u_leaf", "s1__clk[0]", 0, 250)])
        self.assertIn(".s1__clk(clk_c0)", text)
        self.assertEqual(text.count("input wire clk_c0,"), 1)
        self.assertEqual((receipt[0]["previous_net"], receipt[0]["mode"]), ("clk", "rtl"))
        again, _ = K.wire(text, "top", [("clk_c0", "u_bound.u_leaf", "s1__clk[0]", 0, 250)])
        self.assertEqual(again, text)

    def test_one_bit_bus_fails_closed(self):
        src = SOURCE.replace(".ck(clk)", ".s1__clk(clk)")
        rows = [("clk_c0", "u_bound.u_leaf", "s1__clk[0]", 0, 250), ("clk_c1", "u_bound.u_leaf", "s1__clk[1]", 0, 250)]
        with self.assertRaisesRegex(ValueError, "more than one planned bit"):
            K.wire(src, "top", rows)
        with self.assertRaisesRegex(ValueError, "expected one u_leaf.s1__clk\\[1\\] connection"):
            K.wire(src, "top", [("clk_c0", "u_bound.u_leaf", "s1__clk[1]", 0, 250)])
        with self.assertRaisesRegex(ValueError, "expected one u_leaf.s2__clk\\[0\\] connection"):
            K.wire(src, "top", [("clk_c0", "u_bound.u_leaf", "s2__clk[0]", 0, 250)])
        # an exact bit connection still wins over the base name
        exact = SOURCE.replace(".ck(clk)", ".s1__clk[0](clk)")
        text, _ = K.wire(exact, "top", [("clk_c0", "u_bound.u_leaf", "s1__clk[0]", 0, 250)])
        self.assertIn(".s1__clk[0](clk_c0)", text)

    def test_physical_alias_retains_actual_corner_schedule(self):
        tp = dict(name="leaf.ck", insertion_ps=250, insertion_ff_ps=202.5)
        plan = SimpleNamespace(clock=dict(insertion_ps=250, insertion_ff_ps=202.5), types={"T": {"hard_cores": [
            dict(inst="leaf", module="child", physical_inst="u_bound.u_leaf", physical_master="child")
        ]}})
        with patch.object(G.S, "core_taps", return_value=[("clk_c0", 1, 2, tp)]):
            tt = G.core_tap_rows(plan, "T", "TT")
            ff = G.core_tap_rows(plan, "T", "FF")
        self.assertEqual(tt[0][1:3], ("u_bound.u_leaf", "ck"))
        self.assertEqual(tt[0][4], 250)
        self.assertEqual(ff[0][4], 202.5)

if __name__ == "__main__":
    unittest.main()
