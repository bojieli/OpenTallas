"""struct-close 2026-10-09: rtl_boundary.py (submit-time registered-boundary check) and its submit_lint wiring."""
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
os.environ["CL_STATE"] = tempfile.mkdtemp(prefix="rtlb_state_")
import rtl_boundary as B  # noqa: E402
import submit_lint as S  # noqa: E402

COMB = """module t_comb(input wire clk, input wire [7:0] a, input wire [7:0] b, output wire [7:0] y, output reg [7:0] q);
  assign y = a + b;
  always @(posedge clk) q <= a ^ b;
endmodule
"""
REG = """module t_reg(input wire clk, input wire rst_n, input wire [7:0] a, output reg [7:0] q);
  reg [7:0] a_q;
  always @(posedge clk or negedge rst_n) if (!rst_n) a_q <= 0; else a_q <= a;
  always @(posedge clk) q <= a_q + 8'd1;
endmodule
"""


def spec(top, path, **kw):
    s = {"name": "t", "source": {"commit": "c0ffee"}, "stages": {"route": {"cmd":
         f"OUT=x bash physical/hbm_mtp/route_mtp.sh {{LABEL}} {top} --source {path} --clock-port clk"}}}
    s.update(kw)
    return s


def show_for(files):
    return lambda commit, path: files.get(path)


class Boundary(unittest.TestCase):
    def test_comb_path_warns(self):
        r = B.check(spec("t_comb", "rtl/t.sv"), show_for({"rtl/t.sv": COMB}))
        self.assertEqual(r["verdict"], "WARN")
        self.assertEqual(r["in_to_out_bits"], 8)

    def test_comb_path_refused_when_registered_io(self):
        r = B.check(spec("t_comb", "rtl/t.sv", registered_io=True), show_for({"rtl/t.sv": COMB}))
        self.assertEqual(r["verdict"], "REFUSE")

    def test_registered_passes(self):
        r = B.check(spec("t_reg", "rtl/r.sv", registered_io=True), show_for({"rtl/r.sv": REG}))
        self.assertEqual(r["verdict"], "PASS", r)
        self.assertEqual(r["in_to_reg_max"], 0)
        self.assertIn("rst_n", r["ctrl_ports"])

    def test_unreadable_recipe_skips(self):
        r = B.check({"source": {"commit": "c"}, "stages": {"route": {"cmd": "bash other.sh x"}}}, show_for({}))
        self.assertEqual(r["verdict"], "SKIP")

    def test_submit_lint_refuses_and_warns(self):
        class G:
            def __init__(self, f): self.f = f
            def show(self, c, p): return self.f.get(p)
            def blob(self, c, p): return "x"
        r = S.check(spec("t_comb", "rtl/t.sv", registered_io=True), G({"rtl/t.sv": COMB}))
        self.assertEqual(r["verdict"], "REFUSE")
        self.assertIn("rtl_boundary", r["message"])
        r = S.check(spec("t_comb", "rtl/t.sv"), G({"rtl/t.sv": COMB}))
        self.assertEqual(r["verdict"], "PASS")
        self.assertIn("WARN rtl_boundary", r["message"])


if __name__ == "__main__":
    unittest.main()
