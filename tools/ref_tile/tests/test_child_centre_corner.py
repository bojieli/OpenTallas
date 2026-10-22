"""Pure Tcl corner classification; no OpenROAD simulation required."""
import subprocess
from pathlib import Path

HOOK = Path(__file__).resolve().parents[3] / "physical/common_flow/child_centre_tap.tcl"


def test_child_corner_is_not_contaminated_by_unrelated_libraries():
    text = HOOK.read_text()
    proc = text[text.index("proc ot_cct_corner "):text.index("proc ot_cct_worst ")]
    script = """
proc get_lib_cells {args} {return $::child_cells}
proc get_full_name {o} {return $o}
proc get_libs {args} {return $::libs}
""" + proc + """
set child_cells {child_tt/CHILD child_ff/CHILD}
set libs {child_tt child_ff}
puts [ot_cct_corner CHILD WC]
lappend libs unrelated_ss
puts [ot_cct_corner CHILD WC]
set child_cells {child_ss/CHILD child_ff/CHILD}
puts [ot_cct_corner CHILD WC]
set child_cells {CHILD}
set libs {child_tt child_ff}
puts [ot_cct_corner CHILD WC]
puts [ot_cct_corner CHILD BC]
"""
    run = subprocess.run(["tclsh"], input=script, text=True, capture_output=True, check=True)
    assert run.stderr == ""
    assert run.stdout.splitlines() == ["tt", "tt", "ss", "tt", "ff"]


def test_propagate_all_modes_then_restore_original_state():
    text = HOOK.read_text()
    proc = text[text.index('proc ot_cct_propagate_modes '):text.index('proc ot_cct_tap ')]
    harness = r'''
namespace eval sta {proc cmd_mode_name {} {return $::mode}}
set mode ss
set states [dict create ss {clk 1} ff {clk 0}]
proc get_modes {args} {return {ss ff}}
proc get_property {obj prop} {
  if {$prop eq "name"} {return $obj}
  return [dict get $::states $::mode $obj]
}
proc set_mode {name} {set ::mode $name}
proc all_clocks {} {return clk}
proc set_propagated_clock {clks} {foreach c $clks {dict set ::states $::mode $c 1}}
proc unset_propagated_clock {clks} {foreach c $clks {dict set ::states $::mode $c 0}}
'''
    script = harness + proc + r'''
set before $states
set changes [ot_cct_propagate_modes]
puts "$mode/[dict get $states ss clk]/[dict get $states ff clk]"
puts [dict keys $changes]
ot_cct_restore_modes $changes
puts "$mode/[expr {$before eq $states}]"
'''
    run = subprocess.run(['tclsh'], input=script, text=True, capture_output=True, check=True)
    assert run.stderr == ''
    assert run.stdout.splitlines() == ['ss/1/1', 'ff', 'ss/1']
