"""lec.py gold dead-X clean-up (DIE-QC-97 11-09, QC coll_core ot_qwen_static_slot_ctl).

slang bound-checks a dynamic index (`m[i]`, 6-bit i into 64 entries -> `i < 7'd64 ? m[i] : 1'bx`) and proc leaves
mux chains whose X arm an outer mux on the same select already decides (`eb ? 'x : P` under `eb ? 0 : ...`).  Both
X are unreachable, but the gold flow turned them into gold-only $anyseq inputs in the epoch_abort / fault_cause[0]
cones (x226 x228 x229, x55690 ...: UNPROVEN).  gold_dead_x_cmds() (constant-compare fold DEADX_CMP_V + opt_muxtree
after flatten) removes them exactly; a reachable RTL X must still be a free (don't-care) gold input.
HBM-COLLECT-1 11-09 (xs core): the first form, opt_expr -fine -keepdc, also rewrote every compare against a power
of two (`(ac + k) >= 2048` -> `|sum[11]`), so sibling registers got different next-state supports and 9 compare
points were false differs.  Only compares whose result is a constant may change.
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
FOLD = "techmap -map /o/deadx_cmp.v t:$lt t:$le t:$gt t:$ge"
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
# HBM xs u_leaf carry mask: car[b] = (ac + offset(b)) >= 2048, one mask group of 4 bits (offsets 100..103)
CAR_DUT = r"""
module t(input clk, input [10:0] ac, input ml, input mh, output reg [3:0] q);
  wire [3:0] car;
  for (genvar b = 0; b < 4; b = b + 1) begin : g_c
    assign car[b] = ({21'd0, ac} + 32'(100 + b)) >= 32'd2048;
  end
  always @(posedge clk) for (int b = 0; b < 4; b++) q[b] <= car[b] ? mh : ml;
endmodule
"""
CAR_WRAP = r"""
module lec_top(input clk, input [10:0] ac, input ml, input mh, output [3:0] q);
  t u_dut(.clk(clk), .ac(ac), .ml(ml), .mh(mh), .q(q));
endmodule
"""
# every compare shape the fold distinguishes; the comment is the folded value, or 'var' (left as written)
CMP_DUT = r"""
module c(input [5:0] a, input [3:0] b, output [22:0] y);
  assign y[0] = a < 7'd64;                      // 1
  assign y[1] = a < 7'd63;                      // var
  assign y[2] = a <= 6'd63;                     // 1
  assign y[3] = a <= 6'd62;                     // var
  assign y[4] = a > 6'd63;                      // 0
  assign y[5] = a > 6'd62;                      // var
  assign y[6] = a >= 0;                         // 1
  assign y[7] = a >= 7'd64;                     // 0
  assign y[8] = a >= 7'd63;                     // var
  assign y[9] = 7'd64 > a;                      // 1 (constant first)
  assign y[10] = 6'd63 >= a;                    // 1
  assign y[11] = 6'd63 < a;                     // 0
  assign y[12] = 0 <= a;                        // 1
  assign y[13] = 7'd64 <= a;                    // 0
  assign y[14] = 32'd2048 <= {b, 8'd0};         // var: power of two inside the range stays a compare
  assign y[15] = $signed(a) < $signed(7'd40);   // var: signed compares are never folded
  assign y[16] = a < 0;                         // 0
  assign y[17] = 0 > a;                         // 0
  assign y[18] = b < 5'd16;                     // 1
  assign y[19] = b < 4'd8;                      // var
  assign y[20] = 40'h10_0000_0000 > a;          // 1 (wide constant)
  assign y[21] = 6'd0 < a;                      // var
  assign y[22] = a <= 0;                        // var
endmodule
"""
CMP_VAR = 9                                     # y[1 3 5 8 14 15 19 21 22] stay compares


def _yosys():
    y = lec.ORFS + "/tools/install/yosys/bin/yosys"
    return y if os.access(y, os.X_OK) else shutil.which("yosys")


def _x_support(aig, amap):
    """{register key: number of free ($anyseq) gold inputs in the support of its next state}"""
    return {k: len([n for n in v if n is None]) for k, v in _support(aig, amap).items()}


def _support(aig, amap):
    """{register key: sorted names in the support of its next state (None = a free $anyseq gold input)}"""
    I, L, ands = aig["I"], aig["L"], aig["ands"]
    name = {}
    for idx, lst in amap["input"].items():
        name[idx + 1] = lst[0][0]                  # splitnets -ports: one bit per input, "ac[0]"
    for idx, lst in amap["latch"].items():
        name[I + 1 + idx] = next((k for n, b in lst for k in [lec.flop_key(n)[0]] if k), lst[0][0])
    out = {}
    for idx, nxt in enumerate(aig["latches"]):
        key = next((k for n, b in amap["latch"].get(idx, ()) for k in [lec.flop_key(n)[0]] if k), None)
        if not key:
            continue
        seen, st, sup = set(), [nxt >> 1], []
        while st:
            v = st.pop()
            if v in seen or v == 0:
                continue
            seen.add(v)
            if v <= I + L:
                sup.append(name.get(v))
            else:
                k = v - I - L - 1
                st += [ands[2 * k] >> 1, ands[2 * k + 1] >> 1]
        out[key] = sorted(sup, key=str)
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
        a, b = lines.index(FOLD), lines.index("opt_muxtree")
        self.assertEqual(lines[a - 1], "flatten -noscopeinfo")
        self.assertEqual(b, a + 1)
        self.assertLess(b, s.splitlines().index("select -write /o/gold.keep w:* a:lec_keep %i"))
        self.assertLess(b, lines.index("write_json /o/gold.aliases.json"))
        # don't-care semantics kept: no pass that may choose a value for an X
        self.assertNotIn("-mux_undef", s)
        self.assertNotIn("-undriven -zero", s)
        # HBM-COLLECT-1: no fine-grained rewrite of compares that are not constant
        self.assertNotIn("opt_expr -fine", s)

    def test_opt_out_restores_previous_script(self):
        with patch.dict(os.environ, {KEY: "0"}, clear=True):
            s = self._script()
        self.assertNotIn("opt_muxtree", s)
        self.assertNotIn("deadx_cmp", s)
        with patch.dict(os.environ, {}, clear=True):
            on = self._script()
        self.assertEqual([x for x in on.splitlines() if x not in (FOLD, "opt_muxtree")], s.splitlines())

    def test_map_beside_the_gold_output(self):
        self.assertEqual(lec.gold_dead_x_map(Path("/x/lec") / "gold"), "/x/lec/deadx_cmp.v")
        self.assertIn("_TECHMAP_FAIL_", lec.DEADX_CMP_V)
        self.assertIn('techmap_celltype = "$lt $le $gt $ge"', lec.DEADX_CMP_V)


@unittest.skipUnless(_yosys(), "yosys (ORFS image) not available")
class GoldDeadXYosysTests(unittest.TestCase):
    def _gold_aig(self, deadx, dut=DUT, wrap=WRAP_V):
        d = Path(self._tmp())
        (d / "t.sv").write_text(dut)
        (d / "stubs.v").write_text("\n")
        (d / "wrap_gold.v").write_text(wrap)
        (d / "lecff.v").write_text(lec.LECFF_V)
        Path(lec.gold_dead_x_map(d / "gold")).write_text(lec.DEADX_CMP_V)
        env = {"DESIGN_NAME": "t", "VERILOG_FILES": str(d / "t.sv")}
        with patch.dict(os.environ, {} if deadx else {KEY: "0"}, clear=True), \
                patch.object(lec, "rtl_standard_libs", return_value=[]):
            s = lec.gold_script(env, str(d), "slang", [], d / "stubs.v", d / "wrap_gold.v", d / "lecff.v", d / "gold")
        lec.run_yosys(s, d / "gold.ys", None)
        return lec.read_aig(d / "gold.aig"), lec.read_map(d / "gold.map")

    def _gold(self, deadx):
        return _x_support(*self._gold_aig(deadx))

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

    def test_power_of_two_compare_keeps_its_cone(self):
        """HBM xs: with opt_expr -fine q[0] (offset 100 = 0 mod 4) lost ac[1:0] while q[3] kept them, and the
        missing same-support relation q[3] == q[0] made 9 false differs.  The dead-X step must not change it."""
        on = _support(*self._gold_aig(True, CAR_DUT, CAR_WRAP))
        off = _support(*self._gold_aig(False, CAR_DUT, CAR_WRAP))
        for b in range(4):
            self.assertEqual(on[f"u_dut.q[{b}]"], off[f"u_dut.q[{b}]"], (b, on, off))
            self.assertIn("ac[0]", on[f"u_dut.q[{b}]"], on)
            self.assertIn("ac[1]", on[f"u_dut.q[{b}]"], on)

    def test_compare_fold_only_constants_and_exact(self):
        """the DEADX_CMP_V map: the 14 constant-result compares are replaced (the map emits only constants), the 9
        others stay, and the mapped module is equivalent to the original for every input"""
        d = Path(self._tmp())
        (d / "c.v").write_text(CMP_DUT)
        (d / "deadx_cmp.v").write_text(lec.DEADX_CMP_V)
        lec.run_yosys("\n".join([
            f"read_verilog -sv {d / 'c.v'}", "proc", "design -save orig",
            f"techmap -map {d / 'deadx_cmp.v'} t:$lt t:$le t:$gt t:$ge", "opt_expr -keepdc", "opt_clean",
            f"select -assert-count {CMP_VAR} t:$lt t:$le t:$gt t:$ge",
            "rename c mapped", "design -copy-from orig -as c c",
            "miter -equiv -flatten -make_outputs c mapped miter", "hierarchy -top miter",
            "sat -verify -prove trigger 0 miter"]) + "\n",
            d / "cmp.ys", None)


if __name__ == "__main__":
    unittest.main()
