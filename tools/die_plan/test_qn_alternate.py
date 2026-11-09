import json, os, re, subprocess, sys, tempfile, unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent

NET = """module top (input wire clk, input wire rst_n, input wire [8:0] a_i, input wire [4:0] b_i, output wire [7:0] a_o, output wire [7:0] t_o, output wire [3:0] b_o, output wire b_oe);
    wire [7:0] a0_q; wire a0_eq; wire [7:0] a1_q; wire a1_eq; wire [7:0] a2_q; wire a2_eq;
    wire [7:0] t0_q; wire t0_eq; wire [7:0] t1_q; wire t1_eq;
    wire [4:0] b0_v; wire [4:0] b1_v;
    ot_dp_st #(.W(8)) u_a0 (.clk(clk), .rst_n(rst_n), .d(a_i[7:0]), .ea(a_i[8]), .q(a0_q), .eq(a0_eq));
    ot_dp_st #(.W(8)) u_a1 (.clk(clk), .rst_n(rst_n), .d(a0_q), .ea(a0_eq), .q(a1_q), .eq(a1_eq));
    ot_dp_st #(.W(8)) u_a2 (.clk(clk), .rst_n(rst_n), .d(a1_q), .ea(a1_eq), .q(a2_q), .eq(a2_eq));
    assign a_o = a2_q;
    ot_dp_st #(.W(8)) u_t0 (.clk(clk), .rst_n(rst_n), .d(a_i[7:0]), .ea(a_i[8]), .q(t0_q), .eq(t0_eq));
    ot_dp_st #(.W(8)) u_t1 (.clk(clk), .rst_n(rst_n), .d(t0_q), .ea(t0_eq), .q(t1_q), .eq(t1_eq));
    assign t_o = t1_q ^ t0_q;
    ot_dp_st #(.W(4)) u_b0 (.clk(clk), .rst_n(rst_n), .d(b_i[3:0]), .ea(b_i[4]), .q(b0_v[3:0]), .eq(b0_v[4]));
    ot_dp_st #(.W(4)) u_b1 (.clk(clk), .rst_n(rst_n), .d(b0_v[3:0]), .ea(b0_v[4]), .q(b1_v[3:0]), .eq(b1_v[4]));
    assign b_o = b1_v[3:0]; assign b_oe = b1_v[4];
endmodule
"""


class QnAlternate(unittest.TestCase):
    def run_tool(self, text):
        with tempfile.TemporaryDirectory() as d:
            src, dst, rep = (os.path.join(d, n) for n in ("in.sv", "out.sv", "rep.json"))
            Path(src).write_text(text)
            subprocess.run([sys.executable, "-I", str(HERE / "qn_alternate.py"), src, dst, rep], check=True, capture_output=True)
            return Path(dst).read_text(), json.loads(Path(rep).read_text())

    def test_pairs_tail_and_tapped_wire(self):
        out, rep = self.run_tool(NET)
        kinds = dict(re.findall(r"(ot_dp_stn?) #\(\.W\(\d+\)\) (u_\w+)", out)[i][::-1] for i in range(7))
        # odd chain a0-a1-a2: first pair inverted, the tail keeps true polarity
        self.assertEqual([kinds["u_a0"], kinds["u_a1"], kinds["u_a2"]], ["ot_dp_stn", "ot_dp_stn", "ot_dp_st"])
        # t0_q is read by logic as well as by u_t1: no link, both stay plain
        self.assertEqual([kinds["u_t0"], kinds["u_t1"]], ["ot_dp_st", "ot_dp_st"])
        # one vector carrying data + epoch is linked when the next ea is this eq
        self.assertEqual([kinds["u_b0"], kinds["u_b1"]], ["ot_dp_stn", "ot_dp_stn"])
        self.assertEqual(rep["converted"], 4)
        for ln in out.splitlines():
            if "ot_dp_stn #(.W(" in ln:
                self.assertIn(" .qn(", ln)
                self.assertNotIn(" .q(", ln)
        self.assertIn("(* keep_hierarchy, keep *)\nmodule ot_dp_stn", out)
        self.assertIn("reg [W-1:0] q;", out)

    def test_untouched_lines(self):
        out, _ = self.run_tool(NET)
        a = [l for l in NET.splitlines() if "ot_dp_st " not in l]
        b = [l for l in out.splitlines() if "ot_dp_st" not in l][: len(a)]
        self.assertEqual(a, b)


if __name__ == "__main__":
    unittest.main()
