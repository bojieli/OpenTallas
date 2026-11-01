"""DIE-HEAD-53 11-01: parameterised hard-macro instances get a header-only blackbox (hd_lep0N GEN_LINT CHB class)."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gen_phys as G  # noqa: E402

HDR = "module m_pair #(parameter [0:0] CHB=1'b1)( // c\n input wire clk, output wire [3:0] q /* (x) */\n);"


class MacroParamBB(unittest.TestCase):
    def setUp(self):
        self.t = Path(tempfile.mkdtemp())
        (self.t / "src").mkdir()
        (self.t / "kit").mkdir()
        (self.t / "src" / "m_pair.sv").write_text(HDR + "\n reg r; always @(posedge clk) r <= 1; assign q = 0;\nendmodule\n")
        (self.t / "src" / "m_sram.sv").write_text("module m_sram(input wire a); endmodule\n")
        self.top = self.t / "src" / "top.sv"
        self.top.write_text("module top(input wire clk); m_pair #(.CHB(1'b0)) u_p(.clk(clk), .q());\n"
                            " m_sram u_s(.a(clk)); endmodule\n")
        self.macros = [("u_p", "m_pair", "", "", 0, 0, "N"), ("u_s", "m_sram", "", "", 0, 0, "N")]

    def test_param_instance_gets_header_blackbox(self):
        out = G.macro_param_blackboxes(self.macros, [self.top], self.t / "kit")
        self.assertEqual([p.name for p in out], ["m_pair_bb.v"])
        txt = out[0].read_text()
        self.assertIn("(* blackbox *)", txt)
        self.assertIn("parameter [0:0] CHB=1'b1", txt)
        self.assertIn("output wire [3:0] q", txt)
        self.assertNotIn("always", txt)
        self.assertTrue(txt.rstrip().endswith("endmodule"))

    def test_existing_bb_and_unparameterised_untouched(self):
        bb = self.t / "src" / "m_pair_bb.v"
        bb.write_text("(* blackbox *) module m_pair #(parameter CHB=1)(input clk, output [3:0] q); endmodule\n")
        self.assertEqual(G.macro_param_blackboxes(self.macros, [self.top, bb], self.t / "kit"), [])

    def test_root_rtl_fallback_and_missing_header(self):
        root = self.t / "root"
        (root / "rtl" / "x").mkdir(parents=True)
        (self.t / "src" / "m_pair.sv").rename(root / "rtl" / "x" / "m_pair.sv")
        self.assertEqual(len(G.macro_param_blackboxes(self.macros, [self.top], self.t / "kit", root)), 1)
        with self.assertRaises(ValueError):
            G.macro_param_blackboxes(self.macros, [self.top], self.t / "kit", self.t / "none")


if __name__ == "__main__":
    unittest.main()
