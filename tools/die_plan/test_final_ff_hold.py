"""Final hold must be checked after legalization/routing in real TT/FF modes."""
import shutil
import subprocess
from pathlib import Path
import pytest

HERE = Path(__file__).resolve().parent

def run_case(tmp_path, *, after_ff=1., after_tt=27.43, before_ff=-.34, mode="tc", changed_clock=False):
    rc = tmp_path/"selected_rc.tcl"
    rc.write_text("# selected kit model\n")
    helper = HERE/"final_ff_hold.tcl"
    script = r"""
set ::env(OT_HOLD_MM) 1
set ::env(OT_HOLD_FF_MARGIN) 0
set ::env(RESULTS_DIR) {@OUT@}
set ::env(LAYER_PARASITICS_FILE) {@RC@}
set ::ot_mm_active 1
set ::ot_mm_stage 4_cts.sdc
set ::tt 27.43
set ::ff @BEFORE@
set ::calls {}
proc ot_mm_sc {} {return {@MODE@}}
proc ot_mm_sync {} {lappend ::calls sync; set ::ot_mm_synced 1}
proc ot_mm_unsync {} {lappend ::calls unsync; unset -nocomplain ::ot_mm_synced}
proc ot_mm_ws {kind scene} {expr {$kind eq "max" ? $::tt : $::ff}}
proc estimate_parasitics {args} {lappend ::calls estimate}
proc global_route {args} {lappend ::calls "route:$args"}
proc repair_timing {args} {lappend ::calls "repair:$args"; set ::ff 0.2}
proc detailed_placement {} {lappend ::calls dpl; set ::ff @AFTER_FF@; set ::tt @AFTER_TT@}
proc check_placement {args} {lappend ::calls placement_check}
proc write_db {args} {lappend ::calls failed_checkpoint}
proc ot_clk_freeze {args} {lappend ::calls freeze}
proc ot_clk_freeze_assert {args} {lappend ::calls freeze_assert}
proc ot_clk_dump {args} {lappend ::calls clock_dump}
proc set_clock_latency {args} {error "clock frame must not change"}
source {@HELPER@}
rename source real_source
proc source {file} {
 if {[file tail $file] eq "clk_freeze.tcl"} {return}
 uplevel 1 [list real_source $file]
}
rename exec real_exec
proc exec {args} {
 lappend ::calls clock_diff
 if {@CLOCK_CHANGE@} {error "CLK_GEOM_DIFF FAIL"}
 return "CLK_GEOM_DIFF PASS"
}
set result [catch {ot_final_ff_hold} msg]
puts "RESULT $result $msg"
puts "CALLS $::calls"
"""
    for a,b in {"@OUT@":str(tmp_path),"@RC@":str(rc),"@HELPER@":str(helper),
                "@BEFORE@":str(before_ff),"@AFTER_FF@":str(after_ff),"@AFTER_TT@":str(after_tt),
                "@MODE@":mode,"@CLOCK_CHANGE@":str(int(changed_clock))}.items():
        script=script.replace(a,b)
    proc=subprocess.run([shutil.which("tclsh") or "tclsh"],input=script,text=True,capture_output=True,check=True)
    assert not proc.stderr, proc.stderr
    return proc.stdout


def test_final_pass_preserves_frame_and_checks_after_legalization(tmp_path):
    text=run_case(tmp_path)
    assert "RESULT 0" in text and "PASS repaired and rechecked" in text
    assert "repair:-hold -hold_margin 0 -max_buffer_percent 100" in text
    assert text.index("dpl") < text.index("clock_diff")
    assert "failed_checkpoint" not in text


def test_post_legalization_hold_miss_is_a_failure(tmp_path):
    text=run_case(tmp_path,after_ff=-.1)
    assert "RESULT 1" in text and "FAIL after legalization/routing" in text
    assert "failed_checkpoint" in text


def test_setup_damage_cannot_hide_behind_hold_pass(tmp_path):
    text=run_case(tmp_path,after_tt=-1.)
    assert "RESULT 1" in text and "TT setup -1.0" in text


def test_clock_edit_is_a_failure(tmp_path):
    text=run_case(tmp_path,changed_clock=True)
    assert "RESULT 1" in text and "clock geometry changed" in text


def test_wc_setup_mode_is_rejected(tmp_path):
    text=run_case(tmp_path,mode="WC")
    assert "RESULT 1" in text and "actual patched TT/BC GRT session required" in text
    assert "repair:" not in text


def test_already_closed_hold_does_not_pad(tmp_path):
    text=run_case(tmp_path,before_ff=.1)
    assert "RESULT 0" in text and "PASS no repair needed" in text
    assert "repair:" not in text and "freeze" not in text
