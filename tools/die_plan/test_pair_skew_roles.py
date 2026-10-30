"""Clock roles follow real timing arcs, including SRAM write-only WCLK.

The measured HEAD witness had launch469.864314ps, RCLK408.084955ps,
WCLK446.200743ps and CPPR1.030053ps. Selecting RCLK invented38.115788ps
of verify error. These fixtures use the native report_edges text grammar.
"""
from pathlib import Path
import subprocess

SRC = Path(__file__).with_name('pair_skew.tcl')


def run(body):
    prefix = r'''
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
  direction {return [expr {$p in {mem/rd ff/Q} ? "output" : "input"}]}
  is_clock {return [expr {$p eq "ff/CLK"}]}
  ref_name {return [expr {$p eq "mem" ? "SRAM" : "DFF"}]}
  lib_pin_name {return [lindex [split $p /] end]}
  clocks {return clk}
  sources {return src}
 }
 error $prop
}
proc report_edges {args} {
 set p [lindex $args end]
 switch $p {
  mem/wd {if {[lindex $args 0] eq "-from"} {set ::report "";return};set ::report "WCLK -> wd setup\n  ^ -> ^ 1:2\n  ^ -> v 2:3\nWCLK -> wd hold\n  ^ -> ^ 1:2\n"}
  mem/rd {set ::report "RCLK -> rd Reg Clk to Q\n  ^ -> ^ 1:2\n  ^ -> v 2:3\n"}
  ff/CLK {set ::report [expr {[lindex $args 0] eq "-from" ? "CLK -> Q Reg Clk to Q\n  v -> ^ 1:2\n" : ""}]}
  ff/Q {set ::report "CLK -> Q Reg Clk to Q\n  v -> ^ 1:2\n  v -> v 2:3\n"}
  default {error "unexpected pin $p"}
 }
}
'''.replace('@SOURCE@', str(SRC))
    p = subprocess.run(['tclsh'], input=prefix + body, text=True, capture_output=True)
    assert p.returncode == 0 and not p.stderr, p.stderr
    return p.stdout.strip().splitlines()


def test_read_write_and_negative_launch_roles():
    assert run('''
puts [ot_ps_clock_role mem/wd setup]
puts [ot_ps_clock_role mem/wd hold]
puts [ot_ps_clock_role mem/rd clkq]
puts [ot_ps_clock_role ff/Q clkq]
puts [ot_ps_clock_role ff/CLK clkq]
''') == ['mem/WCLK rise', 'mem/WCLK rise', 'mem/RCLK rise', 'ff/CLK fall', 'ff/CLK fall']


def test_ambiguous_related_clock_fails_closed():
    assert run('''
rename report_edges original_report_edges
proc report_edges {args} {set ::report "WCLK -> wd setup\\n  ^ -> ^ 1:2\\nRCLK -> wd setup\\n  ^ -> ^ 1:2\\n"}
puts [catch {ot_ps_clock_role mem/wd setup} message]
puts [string match {*ambiguous setup clock/edge*} $message]
''') == ['1', '1']


def test_write_only_clock_added_and_actual_targets_preserved():
    assert run('''
set ::ot_ps_method tag
set ::ot_ps_tpin [dict create mem/RCLK 10 mem/WCLK 20]
proc all_registers {args} {return {mem/RCLK}}
proc ot_ps_edge {p} {return rise}
proc ot_ps_ckarr {p clk which {rf rise}} {
 set a [dict get [dict create mem/RCLK {410 408.084954717} mem/WCLK {450 446.200743021} src {0 0}] $p]
 return [lindex $a [expr {$which eq "max" ? 0 : 1}]]
}
ot_ps_regs
set w [ot_ps_add_clock {*}[ot_ps_clock_role mem/wd setup]]
set r [ot_ps_add_clock {*}[ot_ps_clock_role mem/rd clkq]]
puts [list [dict size $::ot_ps_R] [lindex [dict get $::ot_ps_R $w] 0] [ot_ps_off $w] [ot_ps_off $r]]
set raw [expr {469.864314123-[lindex [dict get $::ot_ps_R $w] 3]}]
puts [format %.6f [expr {$raw-1.030053}]]
# A second active edge of the same physical pin retains its offset without
# counting that target-file pin twice.
set wf [ot_ps_add_clock mem/WCLK fall]
puts [list [ot_ps_off $wf] [dict size $::ot_ps_tmatched]]
''') == ['2 mem/WCLK 20 10', '22.633518', '20 2']


def test_capture_only_input_with_no_forward_edges_is_not_a_launch():
    assert run('''
set ::ot_ps_nonlaunch_cache {}
puts [ot_ps_capture_only_input mem/wd]
puts [ot_ps_capture_only_input mem/rd]
puts [ot_ps_capture_only_input ff/CLK]
''') == ['1', '0', '0']


def test_through_arc_unknown_report_and_api_error_cannot_exclude_input():
    assert run('''
rename report_edges original_report_edges
proc report_edges {args} {
 if {[lindex $args 0] ne "-from"} {original_report_edges {*}$args;return}
 if {$::case eq "error"} {error "native reporter failed"}
 set ::report [expr {$::case eq "through" ? "wd -> rd combinational\\n  ^ -> ^ 1:2\\n" : "unexpected native report"}]
}
foreach case {through unknown} {
 set ::ot_ps_nonlaunch_cache {}
 puts [ot_ps_capture_only_input mem/wd]
}
set ::case error;set ::ot_ps_nonlaunch_cache {}
puts [catch {ot_ps_capture_only_input mem/wd} message]
puts [string match {*report_edges failed*} $message]
''') == ['0', '0', '1', '1']
