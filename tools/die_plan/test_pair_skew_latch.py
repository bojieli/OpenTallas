"""Level-sensitive latches launch through the Liberty "Latch En to Q" arc (S81-CORES-KITS-11 10-31).

dsfd_bf_front_roots_ck10 (lockup latch busy_pin_d, DLLx1, RTL always_latch if (!clk)) stopped its GRT insertion gate with
"ot_ps_related: unresolved sequential launch clock for u_view.g_pin.busy_pin_d$_DLATCH_N_/CLK": get_fanin returns the
latch CLK pin as the startpoint, and the asap7lock OpenROAD prints that arc as "CLK -> Q Latch En to Q" (checked on
DLLx1_ASAP7_75t_R), which the clkq role ("Clk to Q" only) did not accept.  Stubbed OpenSTA in plain tclsh."""
from pathlib import Path
import subprocess

SRC = Path(__file__).with_name("pair_skew.tcl")

# report_edges -from DLLx1/CLK as printed by the asap7lock OpenROAD (DLLx1: transparent while CLK low, opens on fall)
LATCH = "CLK -> D setup\n  ^ -> ^ 5.0:5.0\nCLK -> Q Latch En to Q\n  v -> ^ 22.82:22.82\n  v -> v 36.40:36.40\n"


def run(body):
    prefix = r"""
set ::ot_ps_lib_only 1
source @SOURCE@
namespace eval sta {
 proc redirect_string_begin {} {set ::report ""}
 proc redirect_string_end {} {return $::report}
}
proc get_full_name {p} {return $p}
proc get_cells {args} {return [ot_ps_inst [lindex $args end]]}
proc get_pins {args} {return [lindex $args end]}
proc get_property {p prop} {
 switch $prop {
  ref_name {return DLLx1_ASAP7_75t_R}
  lib_pin_name {return [lindex [split $p /] end]}
 }
 error $prop
}
proc report_edges {args} {set ::report [expr {[lindex $args 0] eq "-from" ? "@LATCH@" : ""}]}
""".replace("@SOURCE@", str(SRC)).replace("@LATCH@", LATCH.replace("\n", "\\n"))
    p = subprocess.run(["tclsh"], input=prefix + body, text=True, capture_output=True)
    assert p.returncode == 0 and not p.stderr, p.stderr
    return p.stdout.strip().splitlines()


def test_latch_enable_is_a_launch_on_its_opening_edge():
    assert run("""
puts [ot_ps_clock_role l/CLK clkq]
puts [ot_ps_edge l/CLK]
""") == ["l/CLK fall", "fall"]


def test_latch_setup_role_unchanged():
    assert run("puts [ot_ps_clock_role l/D setup]") == []
