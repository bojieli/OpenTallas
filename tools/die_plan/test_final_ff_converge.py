"""Executable stale-RC, physical fixed-point, and clock-freeze controls."""
from pathlib import Path
import subprocess

HELPER = Path(__file__).with_name('final_ff_hold.tcl')

def run(tmp_path, *, converge=True, setup_damage=False, clock_damage=False, drv=True):
    rc=tmp_path/'rc.tcl'; rc.write_text('set ::selected 1\nlappend ::calls rc\n')
    script=r'''
set ::env(OT_HOLD_MM) 1
set ::env(OT_HOLD_FF_MARGIN) 5
set ::env(LAYER_PARASITICS_FILE) {@RC@}
set ::env(RESULTS_DIR) {@OUT@}
set ::ot_mm_active 1
set ::ot_mm_stage 4_cts.sdc
set ::selected 0
set ::tt 30
set ::ff -11
set ::drv @DRV@
set ::state 0
set ::calls {}
proc ot_mm_sc {} {return TC}
proc ot_mm_unsync {} {lappend ::calls unsync}
proc ot_mm_sync {} {
 if {!$::selected} {error "MUTANT: stale RC during FF frame measurement"}
 lappend ::calls sync
}
proc ot_mm_ws {kind scene} {expr {$kind eq "max" ? $::tt : $::ff}}
proc estimate_parasitics {args} {lappend ::calls estimate}
proc global_route {args} {lappend ::calls [list route {*}$args]}
proc repair_design_helper {} {lappend ::calls drv;set ::drv 0; incr ::state}
proc repair_timing {args} {lappend ::calls [list hold {*}$args];set ::ff 5;incr ::state}
proc detailed_placement {} {
 lappend ::calls dpl
 if {!@CONVERGE@} {set ::ff -11;set ::state 0}
 if {@SETUP_DAMAGE@} {set ::tt -1}
}
proc check_placement {args} {lappend ::calls placement}
proc write_db {args} {lappend ::calls failed_checkpoint}
proc ot_clk_freeze {args} {lappend ::calls freeze}
proc ot_clk_freeze_assert {args} {lappend ::calls freeze_assert}
proc ot_clk_dump {args} {lappend ::calls dump}
source {@HELPER@}
rename ot_final_ff_state real_state
proc ot_final_ff_state {} {return $::state}
rename ot_final_ff_counts real_counts
proc ot_final_ff_counts {} {list $::drv 0}
rename source real_source
proc source {file} {
 if {[file tail $file] eq "clk_freeze.tcl"} {return}
 uplevel 1 [list real_source $file]
}
rename exec real_exec
proc exec {args} {
 lappend ::calls clock_diff
 if {@CLOCK_DAMAGE@} {error "clock geometry mutant"}
 return PASS
}
set status [catch {ot_final_ff_converge} msg]
puts "RESULT $status $msg"
puts "CALLS $::calls"
'''
    for key,value in dict(RC=rc,OUT=tmp_path,HELPER=HELPER,CONVERGE=int(converge),SETUP_DAMAGE=int(setup_damage),CLOCK_DAMAGE=int(clock_damage),DRV=int(drv)).items():
        script=script.replace('@'+key+'@',str(value))
    r=subprocess.run(['tclsh'],input=script,text=True,capture_output=True,check=True)
    assert not r.stderr,r.stderr
    return r.stdout


def test_actual_rc_precedes_frame_and_drv_is_rerouted_before_hold(tmp_path):
    s=run(tmp_path)
    assert 'RESULT 0' in s and 'PASS actual selected-RC' in s
    assert 'CALLS unsync rc estimate sync rc estimate' in s
    assert 'hold -hold -hold_margin 5 -max_buffer_percent 100' in s
    assert s.index('drv') < s.index('route -end_incremental') < s.index('hold -hold')
    assert 'pass 2 TT_setup 30 FF_hold 5 slew 0 cap 0' in s


def test_stagnant_actual_route_fails_and_keeps_checkpoint(tmp_path):
    s=run(tmp_path,converge=False,drv=False)
    assert 'RESULT 1' in s and 'repeated physical state' in s
    assert 'failed_checkpoint' in s


def test_setup_damage_fails(tmp_path):
    s=run(tmp_path,setup_damage=True)
    assert 'RESULT 1' in s and 'TT setup negative' in s


def test_clock_mutant_caught_before_data_repair(tmp_path):
    s=run(tmp_path,clock_damage=True)
    assert 'RESULT 1' in s and 'clock geometry changed' in s
    assert 'hold -hold' not in s
