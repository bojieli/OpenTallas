#!/usr/bin/env python3
"""DIE-HBM-48: build_split_tops.tie_dead_wires keeps a declared constant tie across a regeneration (fail-closed)."""
import os
import sys
import unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_split_tops as B  # noqa: E402

GEN = "module t (input wire a);\n    wire [31:0] u_sfu__side_y;\n    x u (.side_y(u_sfu__side_y));\nendmodule\n"


class TieDeadWires(unittest.TestCase):
    def test_tie(self):
        out = B.tie_dead_wires(GEN, {"u_sfu__side_y": "32'd0"}, "t")
        self.assertIn("    wire [31:0] u_sfu__side_y = 32'd0;", out)
        self.assertEqual(out.count("u_sfu__side_y"), 2)

    def test_idempotent(self):
        once = B.tie_dead_wires(GEN, {"u_sfu__side_y": "32'd0"}, "t")
        self.assertEqual(B.tie_dead_wires(once, {"u_sfu__side_y": "32'd0"}, "t"), once)

    def test_no_ties_identity(self):
        self.assertEqual(B.tie_dead_wires(GEN, None, "t"), GEN)

    def test_missing_wire_fails(self):
        with self.assertRaises(SystemExit):
            B.tie_dead_wires(GEN, {"u_nope": "1'b0"}, "t")

    def test_assign_driven_fails(self):
        bad = GEN.replace("endmodule", "assign u_sfu__side_y = 32'd1;\nendmodule")
        with self.assertRaises(SystemExit):
            B.tie_dead_wires(bad, {"u_sfu__side_y": "32'd0"}, "t")

    def test_sfu_lane_cfg_and_committed_top(self):
        cfg = B.PIECES["sfu_lane"]
        self.assertEqual(cfg["tie_wires"], {"u_sfu__side_y": "32'd0"})
        f = os.path.join(B.REPO, "rtl", "hbm_accel", "cores_split", "ot_hgi_sfu_core_split3", cfg["top"] + ".sv")
        if os.path.exists(f):
            self.assertIn("wire [31:0] u_sfu__side_y = 32'd0;", open(f).read())


if __name__ == "__main__":
    unittest.main()
