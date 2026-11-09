"""lec.py gold dead-X clean-up (DIE-QC-97 11-09, QC coll_core ot_qwen_static_slot_ctl).

slang bound-checks a dynamic index (`m[i]`, 6-bit i into 64 entries -> `i < 7'd64 ? m[i] : 1'bx`) and proc leaves
mux chains whose X arm an outer mux on the same select already decides (`eb ? 'x : P` under `eb ? 0 : ...`).  Both
X are unreachable, but the gold flow turned them into gold-only $anyseq inputs in the epoch_abort / fault_cause[0]
cones (x226 x228 x229, x55690 ...: UNPROVEN).  gold_dead_x_cmds() (opt_expr -fine -keepdc + opt_muxtree after
flatten) removes them exactly; a reachable RTL X must still be a free (don't-care) gold input.
    python3 -m unittest tools/die_plan/test_lec_gold_dead_x.py
The yosys cases need the ORFS image (yosys with read_slang); they are skipped elsewhere."""
import importlib.util
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("lec", Path(__file__).with_name("lec.py"))
lec = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lec)

KEY = "OT_LEC_GOLD_DEADX"
DUT = r"""
module t(input clk, input rst_n, input [5:0] i, input [5:0] j, input we, input d,
         input eb, input f, input sel, output reg y, output reg ab, output reg z);
  reg [63:0] m;
  // bound check: i / j are 6 bits wide, m has 64 entries -> every index is in range
  always @(posedge clk or negedge rst_n)
    if (!rst_n) begin m <= 0; y <= 0; end
    else begin
      if (we) m[j] <= d;
      y <= m[i];
    end
  // slot_ctl epoch_abort shape: every branch assigns or holds ab; proc's X arms are dead
  always @(posedge clk or negedge rst_n)
    if (!rst_n) ab <= 0;
    else if (eb) ab <= 0;
    else if (!ab) begin if (f) ab <= 1'b1; end
  // a real RTL X: reachable whenever sel = 1 -> stays a don't care
  always @(posedge clk) z <= sel ? 1'bx : d;
endmodule
"""
WRAP_V = r"""
module lec_top(input clk, input rst_n, input [5:0] i, input [5:0] j, input we, input d,
               input eb, input f, input sel, output y, output ab, output z);
  t u_dut(.clk(clk), .rst_n(rst_n), .i(i), .j(j), .we(we), .d(d), .eb(eb), .f(f), .sel(sel), .y(y), .ab(ab), .z(z));
endmodule
"""


def _yosys():
    y = lec.ORFS + "/tools/install/yosys/bin/yosys"
    return y if os.access(y, os.X_OK) else shutil.which("yosys")


def _x_support(aig, amap):
    """{register key: number of free ($anyseq) gold inputs in the support of its next state}"""
    I, L, ands = aig["I"], aig["L"], aig["ands"]
    free = {v for v in range(1, I + 1) if v - 1 not in amap["input"]}
    out = {}
    for idx, nxt in enumerate(aig["latches"]):
        key = next((k for n, b in amap["latch"].get(idx, ()) for k in [lec.flop_key(n)[0]] if k), None)
        if not key:
            continue
        seen, st, xs = set(), [nxt >> 1], set()
        while st:
            v = st.pop()
            if v in seen or v == 0:
                continue
            seen.add(v)
            if v <= I:
                if v in free:
                    xs.add(v)
            elif v > I + L:
                k = v - I - L - 1
                st += [ands[2 * k] >> 1, ands[2 * k + 1] >> 1]
        out[key] = len(xs)
    return out


class GoldScriptTests(unittest.TestCase):
    ENV = {"VERILOG_FILES": "a.v", "DESIGN_NAME": "t"}

    def _script(self):
        with patch.object(lec, "rtl_standard_libs", return_value=[]):
            return lec.gold_script(self.ENV, "/k", "verilog", [], "s.v", "w.v", "f.v", "/o/gold")

    def test_default_on_after_flatten_before_keep_and_aliases(self):
        with patch.dict(os.environ, {}, clear=True):
            s = self._script()
        lines = s.splitlines()
        a, b = lines.index("opt_expr -fine -keepdc"), lines.index("opt_muxtree")
        self.assertEqual(lines[a - 1], "flatten -noscopeinfo")
        self.assertEqual(b, a + 1)
        self.assertLess(b, s.splitlines().index("select -write /o/gold.keep w:* a:lec_keep %i"))
        self.assertLess(b, lines.index("write_json /o/gold.aliases.json"))
        # don't-care semantics kept: no pass that may choose a value for an X
        self.assertNotIn("-mux_undef", s)
        self.assertNotIn("-undriven -zero", s)

    def test_opt_out_restores_previous_script(self):
        with patch.dict(os.environ, {KEY: "0"}, clear=True):
            s = self._script()
        self.assertNotIn("opt_muxtree", s)
        self.assertNotIn("opt_expr -fine", s)
        with patch.dict(os.environ, {}, clear=True):
            on = self._script()
        self.assertEqual([x for x in on.splitlines() if x not in ("opt_expr -fine -keepdc", "opt_muxtree")],
                         s.splitlines())


@unittest.skipUnless(_yosys(), "yosys (ORFS image) not available")
class GoldDeadXYosysTests(unittest.TestCase):
    def _gold(self, deadx):
        d = Path(self._tmp())
        (d / "t.sv").write_text(DUT)
        (d / "stubs.v").write_text("\n")
        (d / "wrap_gold.v").write_text(WRAP_V)
        (d / "lecff.v").write_text(lec.LECFF_V)
        env = {"DESIGN_NAME": "t", "VERILOG_FILES": str(d / "t.sv")}
        with patch.dict(os.environ, {} if deadx else {KEY: "0"}, clear=True), \
                patch.object(lec, "rtl_standard_libs", return_value=[]):
            s = lec.gold_script(env, str(d), "slang", [], d / "stubs.v", d / "wrap_gold.v", d / "lecff.v", d / "gold")
        lec.run_yosys(s, d / "gold.ys", None)
        return _x_support(lec.read_aig(d / "gold.aig"), lec.read_map(d / "gold.map"))

    def _tmp(self):
        t = tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        return t.name

    def test_bound_check_and_dead_proc_x_leave_no_anyseq(self):
        on = self._gold(True)
        self.assertEqual(on["u_dut.y"], 0, on)        # m[i]: i < 64 folded, the X arm is gone
        self.assertEqual(on["u_dut.ab"], 0, on)       # epoch_abort shape: dead proc X arms removed
        self.assertTrue(all(on[f"u_dut.m[{k}]"] == 0 for k in range(64)), on)

    def test_real_x_is_still_a_dont_care(self):
        self.assertGreaterEqual(self._gold(True)["u_dut.z"], 1)

    def test_previous_script_had_the_dead_x(self):
        off = self._gold(False)
        self.assertGreaterEqual(off["u_dut.y"], 1, off)    # the bound-check X arm
        self.assertGreaterEqual(off["u_dut.ab"], 1, off)   # the dead proc X arms (3 with the previous script)
        self.assertGreaterEqual(off["u_dut.z"], 1)


if __name__ == "__main__":
    unittest.main()
