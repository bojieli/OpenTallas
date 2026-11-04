"""Clock sizing policy must allow D-pin buffers and retain prior exclusions."""
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HOOK = ROOT / "physical/die_plan/qwen_kvsys/cores/harden/eco/eco_route.tcl"


def test_clock_master_scope_and_error_cleanup():
    text = HOOK.read_text()
    helper = text[text.index("proc kvc_preserve_clock_masters"):text.index("proc kvc_drv")]
    mock = r"""
set dnu(ff1) 0
set dnu(ff2) 1
set instance_dont_touch 0
proc ot_clk_dbnets {} { return {net} }
proc net {method} { return {pin} }
proc pin {method} { return sink }
proc sink {method args} {
    if {$method eq "getMaster"} {return master}
    error "guard must never change sink instance dont_touch"
}
proc master {method} { return DFFHQNx1_ASAP7_75t_R }
proc get_lib_cells {args} { return {ff1 ff2} }
proc get_property {cell property} {
    if {$property ne "dont_use"} {error "unsupported property"}
    return $::dnu($cell)
}
proc set_dont_use {cells} {foreach cell $cells {set ::dnu($cell) 1}}
proc unset_dont_use {cells} {foreach cell $cells {set ::dnu($cell) 0}}
proc require {value message} { if {![uplevel 1 [list expr $value]]} { error $message } }
proc insert_data_buffer {} {
    require {$::instance_dont_touch == 0} "D-pin buffering blocked"
}
set caller 0
kvc_preserve_clock_masters {
    require {$dnu(ff1) == 1 && $dnu(ff2) == 1} "flop sizing not excluded"
    insert_data_buffer
    set caller 1
}
require {$caller == 1} "lost caller scope"
require {$dnu(ff1) == 1 && $dnu(ff2) == 1} "session flop-size policy lost"
set rc [catch {kvc_preserve_clock_masters {error real_repair_failure}} message]
require {$rc == 1 && $message eq "real_repair_failure"} "repair error swallowed"
require {$dnu(ff1) == 1 && $dnu(ff2) == 1} "repair error cleared existing exclusions"
rename get_lib_cells old_get_lib_cells
proc get_lib_cells {args} {return {}}
set rc [catch {kvc_preserve_clock_masters {error body_must_not_run}} message]
require {$rc == 1 && [string match {*no loaded ASAP7 DFF*} $message]} "missing library choices accepted"
puts PASS
"""
    result = subprocess.run(["tclsh"], input=helper + mock, text=True, capture_output=True)
    assert result.returncode == 0 and "PASS" in result.stdout and not result.stderr, result
