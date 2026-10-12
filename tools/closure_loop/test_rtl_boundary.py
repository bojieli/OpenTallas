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

    def test_cl_spec_refused_by_default(self):
        r = B.check(spec("t_comb", "rtl/t.sv", name="x-tc-cl"), show_for({"rtl/t.sv": COMB}))
        self.assertEqual(r["verdict"], "REFUSE")
        r = B.check(spec("t_comb", "rtl/t.sv", name="x-tc-cl", rtl_boundary={"waive": "immediate-drop ready by design"}),
                    show_for({"rtl/t.sv": COMB}))
        self.assertEqual(r["verdict"], "WARN")
        r = B.check(spec("t_comb", "rtl/t.sv", name="x-tc-cx", registered_io=False), show_for({"rtl/t.sv": COMB}))
        self.assertEqual(r["verdict"], "WARN")

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


WFC_TOP = """module ot_dsrom_wfc_tokpipe_src #(
    parameter integer PROMPT_EXTRA = 0,
    parameter integer REC_SRAM = 1
) (input wire clk, input wire [7:0] a, output reg [7:0] q);
  reg [7:0] a_q;
  initial if (PROMPT_EXTRA > 9) $fatal(1, "bad");
  always @(posedge clk) begin a_q <= a; q <= a_q; end
endmodule
"""


class Ac1(unittest.TestCase):
    """drive-resume (review-0542 AC1): the WFC SOURCE recipe is read; a registered_io:true spec never SKIPs silently"""
    WFC = {"name": "w-cx", "registered_io": True, "source": {"commit": "c0ffee"}, "stages": {"route": {"cmd":
           "export OT_ORFS_CORNER_OVERRIDE=TC; python3 tools/dsrom_wfc_tokpipe_physical.py prep --inst src --case {RUN}/route"}}}

    def test_wfc_recipe(self):
        files = {"physical/dsrom_wfc_tokpipe/src_basis.json": '{"params": {"PROMPT_EXTRA": 2, "REC_SRAM": 0, "WAVE": 1}}',
                 "rtl/dsrom_sys/mtp/ot_dsrom_wfc_tokpipe_src.sv": WFC_TOP}
        r = B.recipe(self.WFC, show_for(files))
        self.assertEqual(r["top"], "ot_dsrom_wfc_tokpipe_src")
        self.assertEqual(r["params"], {"PROMPT_EXTRA": "2", "REC_SRAM": "0"})      # WAVE is not a top parameter
        self.assertNotIn(B.WFC_MACRO_BB, r["sources"])
        files["rtl/rom/wavefront/ot_rom_pkg_ctrl_wfc_tokpipe.sv"] = "module unused_ctrl(input wire x); endmodule\n"
        self.assertEqual(B.check(self.WFC, show_for(files))["verdict"], "PASS")   # $fatal guard elaborates

    def test_requested_check_that_cannot_run_refuses(self):
        r = B.check(self.WFC, show_for({}))
        self.assertEqual(r["verdict"], "REFUSE")
        self.assertIn("cannot run", r["message"])
        waived = dict(self.WFC, rtl_boundary={"waive": "unchanged closed SOURCE ports"})
        self.assertEqual(B.check(waived, show_for({}))["verdict"], "WARN")
        default_strict = {k: v for k, v in self.WFC.items() if k != "registered_io"}
        self.assertEqual(B.check(default_strict, show_for({}))["verdict"], "SKIP")

    def test_explicit_recipe(self):
        s = dict(spec("nope", "rtl/none.sv"), registered_io=True,
                 rtl_boundary={"top": "t_reg", "sources": ["rtl/t.sv"]})
        self.assertEqual(B.check(s, show_for({"rtl/t.sv": REG}))["verdict"], "PASS")


if __name__ == "__main__":
    unittest.main()
