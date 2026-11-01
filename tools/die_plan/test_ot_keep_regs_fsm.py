"""KIT-TRIAGE-1/LEC 11-01: physical/common_flow/ot_keep_regs.tcl keeps FSM state registers in their RTL encoding by default
(fsm_encoding "none" on every register output wire without its own fsm_encoding), so lec.py matches them by name; yosys'
one-hot re-encoding (kshare lane.st 3 -> 6 bits, h9b state 2 -> 4 bits) left gold-only state registers and NOT EQUIVALENT.
OT_FSM_RECODE=1 restores the re-encoding; an RTL fsm_encoding attribute still wins.  The yosys cases run where yosys is
on PATH (ORFS image) and skip elsewhere.
    python3 -m unittest tools/die_plan/test_ot_keep_regs_fsm.py"""
import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HOOK = ROOT / "physical" / "common_flow" / "ot_keep_regs.tcl"

FSM = """module top (input wire clk, rst_n, input wire [1:0] go, output reg [1:0] o);
  %s reg [2:0] st;
  always @(posedge clk or negedge rst_n)
    if (!rst_n) st <= 3'd0;
    else case (st)
      3'd0: st <= go[0] ? 3'd1 : 3'd0;
      3'd1: st <= go[1] ? 3'd2 : 3'd3;
      3'd2: st <= 3'd4;
      3'd3: st <= 3'd0;
      3'd4: st <= go[0] ? 3'd0 : 3'd4;
      default: st <= 3'd0;
    endcase
  always @(posedge clk) o <= {st == 3'd4, st == 3'd2};
endmodule
"""

DRIVE = r"""yosys -import
read_verilog -sv $::env(SRC)
hierarchy -check -top top
source $::env(HOOK)
synth -flatten -top top
puts "DFFBITS [string trim [tee -q -s result.string select -count t:\$_*DFF*]]"
"""


class HookText(unittest.TestCase):
    def test_default_on_block_with_opt_out(self):
        t = HOOK.read_text()
        i_proc, i_fsm = t.index("\nyosys proc\n"), t.index("OT_FSM_KEEP")
        self.assertLess(i_proc, i_fsm, "the register selection needs the processes elaborated first")
        self.assertIn('$::env(OT_FSM_RECODE) eq "1"', t)
        self.assertIn("a:fsm_encoding %d", t, "an RTL fsm_encoding attribute must not be overwritten")


@unittest.skipUnless(shutil.which("yosys"), "yosys not on PATH (run inside the ORFS image)")
class HookYosys(unittest.TestCase):
    def run_case(self, attr="", env=None):
        with tempfile.TemporaryDirectory() as d:
            src, tcl = Path(d) / "top.sv", Path(d) / "drive.tcl"
            src.write_text(FSM % attr)
            tcl.write_text(DRIVE)
            e = {k: v for k, v in os.environ.items() if k != "OT_FSM_RECODE"}
            e.update(SRC=str(src), HOOK=str(HOOK), **(env or {}))
            p = subprocess.run(["yosys", "-q", "-c", str(tcl)], capture_output=True, text=True, env=e, timeout=300)
            out = p.stdout + p.stderr
            self.assertEqual(p.returncode, 0, out[-3000:])
            m = re.search(r"DFFBITS (\d+)", out)
            self.assertIsNotNone(m, out[-3000:])
            return int(m.group(1)), out

    def test_default_keeps_binary_state(self):
        n, out = self.run_case()
        self.assertIn("OT_FSM_KEEP: fsm_encoding none on", out)
        self.assertEqual(n, 5, "3 binary state bits + 2 output bits")

    def test_opt_out_recodes(self):
        n, out = self.run_case(env={"OT_FSM_RECODE": "1"})
        self.assertNotIn("OT_FSM_KEEP", out)
        self.assertGreater(n, 5, "yosys re-encodes the 5-state FSM (one-hot)")

    def test_rtl_attribute_wins(self):
        n, _ = self.run_case(attr='(* fsm_encoding = "one-hot" *)')
        self.assertGreater(n, 5, "an explicit RTL one-hot request is still honoured")


if __name__ == "__main__":
    unittest.main()
