"""Tcl control-flow/sentinel controls only; no native PG/filler qualification."""
from pathlib import Path
import subprocess
import pytest
DRIVER=Path(__file__).parents[2]/'results/flow/native_pg_fill_1102_PREP/fillcell_driver.tcl'
BASE='''set ::env(FILL_CELLS) FILLER_ASAP7_75t_R
set ::env(PRE_FILLCELL_TCL) /work/pg_fill_pre.tcl
set ::env(POST_FILLCELL_TCL) /work/pg_fill_post.tcl
set ::births 0;set ::active 1;set ::native_ok 1;set ::end_error 0
proc filler_placement {args} {incr ::births}
proc ot_pg_strict_enabled {} {return 1}
proc ot_pg_native_birth_supported {command} {return [expr {$::active && $::native_ok}]}
proc ot_native_pg_status {} {return [dict create active $::active]}
proc ot_pg_native_birth_end {} {set ::active 0;if {$::end_error} {error END_ERROR};return {creates 0 swaps 0 bound 0}}
'''
PRE='set ::ot_pg_fill_baseline_ready 1;set ::ot_pg_fill_pre_complete 1;'
POST='set ::active 0;set ::ot_pg_fill_post_reached 1'
@pytest.mark.parametrize('tag,body,extra,expect,births',[
 ('normal',PRE+'filler_placement;'+POST,'','',1),
 ('rename_follows',PRE+'rename filler_placement ot_pg_unsupported_filler_placement;proc filler_placement {args} {ot_pg_unsupported_filler_placement {*}$args};filler_placement;'+POST,'','',1),
 ('missing_pre','filler_placement','','OT_PG_FILL_PRE_BASELINE_REQUIRED*',0),
 ('missing_baseline','set ::ot_pg_fill_pre_complete 1;filler_placement','','OT_PG_FILL_PRE_BASELINE_REQUIRED*',0),
 ('missing_native',PRE+'set ::native_ok 0;filler_placement','','OT_PG_FILL_REAL_NATIVE_CURRENT_DB_PG0_REQUIRED',0),
 ('wrong_binding',PRE+'filler_placement','set ::env(PRE_FILLCELL_TCL) /wrong','OT_PG_FILL_EXACT_HOOK_REQUIRED*',0),
 ('primary_error',PRE+'error ORIGINAL_BODY_ERROR','set ::end_error 1','ORIGINAL_BODY_ERROR',0),
 ('early_return','return EARLY','','OT_PG_FILL_FULL_POST_NOT_REACHED',0),
 ('missing_post',PRE+'filler_placement','','OT_PG_FILL_FULL_POST_NOT_REACHED',1),
 ('nonlocal_cleanup','set x 1','proc ot_pg_native_birth_end {} {set ::active 0;return -code return EARLY_END}','OT_PG_FILL_CLEANUP_REFUSED*',0),
])
def test_missing_pre_stops_before_factory_and_cleanup_remains_strict(tmp_path,tag,body,extra,expect,births):
    (tmp_path/'fillcell.native_pg_original.tcl').write_text(body+'\n')
    harness=tmp_path/'harness.tcl'
    harness.write_text(BASE+extra+'\nset ::env(SCRIPTS_DIR) {'+str(tmp_path)+'}\n'+'''
set code [catch {source {@DRIVER@}} message]
if {$::births != @BIRTHS@} {error "UNGUARDED_FACTORY $::births"}
if {@FAILED@} {
 if {$code != 1 || ![string match {@EXPECTED@} $message]} {error "wrong failure $code $message"}
} elseif {$code != 0 || $::active} {error "false success $code $message"}
foreach command {filler_placement ot_pg_unsupported_filler_placement} {
 if {[info commands $command] ne "" && [trace info execution $command] ne ""} {error TRACE_LEAK}
}
puts SOURCE_ONLY_PASS
'''.replace('@DRIVER@',str(DRIVER)).replace('@BIRTHS@',str(births)).replace('@FAILED@',str(int(bool(expect)))).replace('@EXPECTED@',expect))
    p=subprocess.run(['tclsh',str(harness)],capture_output=True,text=True)
    assert p.returncode==0 and p.stdout.strip().endswith('SOURCE_ONLY_PASS'),(tag,p.stdout,p.stderr)
