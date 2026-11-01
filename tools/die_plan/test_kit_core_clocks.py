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
