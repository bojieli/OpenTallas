"""DIE-S81-26 10-29 (COORD 10:41 ruling (a) + approval follow-up): declared clock-landing rings become flip-flops per
module (physical/common_flow/ot_keep_regs.tcl OT_LANDING_FF=1, set by gen phys only when the kit RTL defines
ot_dp_clk_landing); SYNTH_MEMORY_MAX_BITS stays at the default, so a non-landing 4097..4608-bit memory in the same kit
still FAILs.  The yosys cases run where yosys is on PATH (ORFS image) and skip elsewhere."""
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gen_phys  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
LANDING = ROOT / "rtl" / "common" / "ot_dp_clk_landing.sv"
FIFO = ROOT / "rtl" / "common" / "ot_meso_fifo.sv"
HOOK = ROOT / "physical" / "common_flow" / "ot_keep_regs.tcl"

TOP = """module top (input wire fclk, clk, rst_n, input wire [1104:0] d, output wire [1104:0] q, output wire ready, fault
`ifdef WITH_PLAIN
  , input wire [1:0] a, input wire we, output wire [1124:0] pq
`endif
);
  ot_dp_clk_landing #(.W(1105)) u_land (.fclk(fclk), .clk(clk), .rst_n(rst_n), .d(d), .q(q), .ready(ready), .fault(fault));
`ifdef WITH_PLAIN
  plain_mem u_pm (.clk(clk), .a(a), .d({20'd0, d}), .we(we), .q(pq));
`endif
endmodule
module plain_mem #(parameter W = 1125) (input wire clk, input wire [1:0] a, input wire [W-1:0] d, input wire we,
                                       output reg [W-1:0] q);
  reg [W-1:0] m [0:3];
  always @(posedge clk) begin if (we) m[a] <= d; q <= m[a]; end
endmodule
"""

DRIVE = r"""yosys -import
set defs {-DSYNTHESIS}
if {[info exists ::env(WITH_PLAIN)]} { lappend defs -DWITH_PLAIN }
foreach f [split $::env(SRCS) " "] { read_verilog -defer -sv {*}$defs $f }
hierarchy -check -top top
source $::env(HOOK)
opt_clean -purge
synth -flatten -top top -run :fine
memory_collect
foreach c [split [string trim [tee -q -s result.string select -list t:\$mem_v2]] "\n"] {
  if {$c eq ""} continue
  set m [lindex [split $c /] 0]; set i [lindex [split $c /] 1]
  puts "MEMBITS [expr {[rtlil::get_param -uint $m $i WIDTH] * [rtlil::get_param -uint $m $i SIZE]}] $c"
}
"""


def test_defines_landing_ring(tmp_path):
    (tmp_path / "top.sv").write_text("module top; ot_dp_clk_landing #(.W(1105)) a (); endmodule\n")
    assert not gen_phys.defines_landing_ring(tmp_path)          # instance only: no declared ring module
    shutil.copyfile(LANDING, tmp_path / "ot_dp_clk_landing.sv")
    assert gen_phys.defines_landing_ring(tmp_path)


def _mems(tmp_path, landing_ff, plain):
    (tmp_path / "top.sv").write_text(TOP)
    (tmp_path / "drive.tcl").write_text(DRIVE)
    env = dict(os.environ, SRCS=f"{tmp_path / 'top.sv'} {LANDING} {FIFO}", HOOK=str(HOOK), OT_LANDING_FF=landing_ff)
    env.pop("WITH_PLAIN", None)
    if plain:
        env["WITH_PLAIN"] = "1"
    r = subprocess.run(["yosys", "-q", "-c", str(tmp_path / "drive.tcl")], env=env, capture_output=True, text=True,
                       timeout=900)
    assert r.returncode == 0, r.stderr[-2000:]
    return [(int(b), n) for b, n in re.findall(r"MEMBITS (\d+) (\S+)", r.stdout)]


yosys = pytest.mark.skipif(shutil.which("yosys") is None, reason="yosys not on PATH (run in the ORFS image)")


@yosys
def test_landing_ring_maps_to_flops(tmp_path):
    assert _mems(tmp_path, "1", False) == []


@yosys
def test_without_flag_ring_is_a_4420_bit_memory(tmp_path):
    mems = _mems(tmp_path, "0", False)
    assert [b for b, _ in mems] == [4420] and "ot_dp_clk_landing" in mems[0][1]


@yosys
def test_non_landing_4500_bit_memory_still_inferred(tmp_path):
    # the same kit with a plain 4 x 1125 = 4500-bit memory: still a memory above 4096 -> the ORFS check FAILs it
    assert [b for b, _ in _mems(tmp_path, "1", True)] == [4500]
