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

    def test_bare_macro_default_takes_identity(self):
        hdr = "module m #(parameter integer A = `A_DEF, parameter integer B = `B_DEF,\n parameter [14:0] C=`C_DEF)(input wire c);"
        out, done = G._header_with_defaults(hdr, {"A": "2", "C": "15'b000001010011100"})
        self.assertIn("A = 2", out)
        self.assertIn("C= 15'b000001010011100", out)
        self.assertIn("B = `B_DEF", out)          # no identity: stays, an override of it still stops synth
        self.assertEqual(sorted(done), ["A", "C"])
        keep, none = G._header_with_defaults("module m #(\n`ifdef X\n parameter integer A = 1\n`else\n parameter integer A = 0\n`endif\n)(input wire c);", {"A": "2"})
        self.assertEqual(none, {})                # a `ifdef-selected declaration stays as written

    def test_param_instance_gets_header_blackbox(self):
        out = G.macro_param_blackboxes(self.macros, [self.top], self.t / "kit")
        self.assertEqual([p.name for p in out], ["m_pair_bb.v"])
        txt = out[0].read_text()
        self.assertIn("(* blackbox *)", txt)
        # DIE-S81-47 11-01: the header default is the instances' common override (the signed identity)
        self.assertIn("parameter [0:0] CHB= 1'b0", txt)
        self.assertIn("output wire [3:0] q", txt)
        self.assertNotIn("always", txt)
        self.assertTrue(txt.rstrip().endswith("endmodule"))

    def test_exact_staged_multimodule_header_precedes_filename_fallback(self):
        packaged = self.t / "src" / "engines.sv"
        (self.t / "src" / "m_pair.sv").rename(packaged)
        packaged.write_text("module other(input wire x); endmodule\n" + packaged.read_text())
        # An unstaged sibling with the conventional basename is not the selected
        # physical module's header when its actual definition is already staged.
        (self.t / "src" / "m_pair.sv").write_text(
            "module m_pair #(parameter CHB=1)(input clk, output [0:0] q); endmodule\n")
        out = G.macro_param_blackboxes(self.macros, [self.top, packaged], self.t / "kit")
        self.assertEqual(len(out), 1)
        # the staged packaged header, with the instances' common override as its default (signed identity)
        self.assertEqual(G._module_header(out[0].read_text(), "m_pair"),
                         G._header_with_defaults(G._module_header(packaged.read_text(), "m_pair"),
                                                 G.macro_instance_identity(self.top.read_text(), "m_pair"))[0])
        self.assertIn("output wire [3:0] q", out[0].read_text())
        self.assertNotIn("module other", out[0].read_text())

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

    def test_identity_only_where_all_instances_agree(self):
        self.top.write_text("module top(input wire clk); m_pair #(.CHB(1'b0)) u_p(.clk(clk), .q());\n"
                            " m_pair #(.CHB(1'b1)) u_q(.clk(clk), .q()); m_sram u_s(.a(clk)); endmodule\n")
        txt = G.macro_param_blackboxes(self.macros, [self.top], self.t / "kit")[0].read_text()
        self.assertIn("parameter [0:0] CHB=1'b1", txt)          # disagreement: RTL default kept
        self.assertNotIn("signed identity", txt)

    def test_staged_copy_loses_the_macro_body_only(self):
        # S81 col class: header + RTL body in one kit = 'Re-definition of module' in LEC (one read per file)
        src = self.t / "src" / "m_pair.sv"
        src.write_text("// endmodule in a comment\n" + HDR + "\n assign q = 0; /* endmodule */\nendmodule\n"
                       "module helper(input wire a); endmodule\n")
        kit = self.t / "kit"
        for f in (self.top, src):
            (kit / f.name).write_text(f.read_text())
        G.macro_param_blackboxes(self.macros, [self.top, src], kit)
        staged = (kit / "m_pair.sv").read_text()
        self.assertNotIn("assign q", staged)
        self.assertIn("module helper", staged)
        self.assertEqual(src.read_text().count("assign q"), 1)     # the source is untouched
        self.assertIn("m_pair #(.CHB(1'b0)) u_p", (kit / "top.sv").read_text())

    def test_ifdef_selected_default_kept(self):
        hdr = ("module m_c #(\n    parameter integer A = 0,\n`ifdef X\n    parameter integer B = 1\n`else\n"
               "    parameter integer B = 0\n`endif\n) (\n    input wire a\n);")
        out, done = G._header_with_defaults(hdr, {"A": "1", "B": "0"})
        self.assertEqual(done, {"A": "1"})
        self.assertIn("`else\n    parameter integer B = 0\n`endif", out)
        self.assertIn("A = 1", out)

    def test_macro_with_fallback_default_takes_identity(self):
        hdr = ("module m_c #(parameter integer A =\n`ifdef A_DEF\n    `A_DEF\n`else\n    0\n`endif\n,\n"
               " parameter integer B =\n`ifdef B_DEF\n    `B_DEF\n`else\n    0\n`endif\n) (input wire a);")
        out, done = G._header_with_defaults(hdr, {"A": "1"})
        self.assertEqual(done, {"A": "1"})
        self.assertIn("A = 1", out)
        self.assertNotIn("`A_DEF", out)
        self.assertIn("`B_DEF", out)              # no identity: stays
        # another macro in the ifdef branch is a real selection, kept
        other = "module m_c #(parameter integer A =\n`ifdef X\n    `Y\n`else\n    0\n`endif\n) (input wire a);"
        self.assertEqual(G._header_with_defaults(other, {"A": "1"}), (other, {}))

    def test_instance_identity_parse(self):
        txt = ("m_x #(.A(2), .B(P_INST), .C(\"s\")) u0 (.a(b));\n// m_x #(.A(9)) u9 ();\n"
               "m_x #(.A(2), .B(P2), .C(\"s\")) u1 (.a(b));\n")
        self.assertEqual(G.macro_instance_identity(txt, "m_x"), {"A": "2"})
        # the definition's own parameter list is not an instance; non-literal overrides do not veto
        txt2 = "module m_x #(parameter A = 0)(input a); endmodule\n" + txt + "m_x #(.A(Q)) u2 ();\n"
        self.assertEqual(G.macro_instance_identity(txt2, "m_x"), {"A": "2"})
        self.assertEqual(G.macro_instance_identity(txt2 + "m_x #(.A(3)) u3 ();", "m_x"), {})
        self.assertEqual(G.macro_instance_identity("m_x #(5) u0 ();", "m_x"), {})


if __name__ == "__main__":
    unittest.main()
