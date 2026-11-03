from pathlib import Path
import tempfile,subprocess,json
R=Path(__file__).parent
COMMON=Path(__file__).parent/'pg_native_qualified_562.tcl'
BASE='''source {@COMMON@}
source {@HELPER@}
set ::counters {creates 0 swaps 0 bound 0}
set ::end_calls 0;set ::status_active 1;set ::end_error 0;set ::audit_bad 0
proc ot_native_pg_audit {} {if {$::audit_bad} {error BAD_PG};return $::counters}
proc ot_native_pg_status {} {return [dict create active $::status_active]}
proc ot_pg_native_birth_end {} {incr ::end_calls;set ::status_active 0;if {$::end_error} {error END_FAILED};return $::counters}
proc add_births {n} {dict incr ::counters creates $n;dict incr ::counters bound [expr {2*$n}]}
set ::ot_pgc::started 1;set ::ot_pgc::active 1;set ::ot_pgc::stage global_place
set ::ot_pgc::fh [open {@LOG@} w];set ::ot_pgc::initial $::counters
'''
CASES={
 'requested_plain_separate_port':'''proc ot_gpl_native {args} {add_births 3;return OK}
proc buffer_ports {args} {add_births 2;return OK}
proc global_placement {args} {ot_gpl_native -density 0.35}
ot_pg_place_canary_after_pre global_place
buffer_ports -inputs
global_placement -timing_driven -routability_driven -density 0.35
if {[dict get [ot_pg_place_canary_finish global_place] state] ne "FINISHED"} {error END}
if {[dict get [ot_pg_place_canary_finish global_place] state] ne "ALREADY_FINISHED" || $::end_calls!=1} {error IDEMPOTENCE}
if {[trace info execution ot_gpl_native] ne "" || [trace info execution global_placement] ne ""} {error TRACE_LEAK}
''',
 'real_error_preserved_for_fallback':'''set ::calls 0
proc ot_gpl_native {args} {incr ::calls;add_births 1;if {$::calls==1} {error GPL-0305};return OK}
proc global_placement {args} {if {[catch {ot_gpl_native {*}$args} res opts]} {if {![string match *GPL-0305* $res]} {return -options $opts $res};return [ot_gpl_native -density 0.35]};return $res}
ot_pg_place_canary_after_pre global_place
global_placement -timing_driven -density 0.35
if {$::calls!=2} {error FALLBACK_CHANGED}
ot_pg_place_canary_finish global_place
''',
 'ordinary_native_error':'''proc ot_gpl_native {args} {error ORDINARY_NATIVE_ERROR}
proc global_placement {args} {ot_gpl_native {*}$args}
ot_pg_place_canary_after_pre global_place
set code [catch {global_placement -timing_driven} why]
if {$code!=1 || $why ne "ORDINARY_NATIVE_ERROR"} {error LOST_NATIVE_ERROR}
ot_pg_place_canary_finish global_place
''',
 'pg_error_blocks_retryable_fallback':'''proc ot_gpl_native {args} {set ::audit_bad 1;error GPL-0305}
proc global_placement {args} {ot_gpl_native {*}$args}
ot_pg_place_canary_after_pre global_place
set code [catch {global_placement -timing_driven} why]
if {$code!=1 || ![string match PG_PLACE_CANARY_POSTCALL_PG_REFUSED* $why] || [string match *GPL-0305* $why]} {error UNSAFE_FALLBACK}
set ::audit_bad 0
ot_pg_place_canary_finish global_place
''',
 'cleanup_failure_stays_failed':'''set ::end_error 1
if {![catch {ot_pg_place_canary_finish global_place} why]} {error FALSE_CLEANUP_PASS}
if {![catch {ot_pg_place_canary_finish global_place} why] || $::end_calls!=1} {error FALSE_SECOND_PASS}
''',
 'status_must_be_inactive':'''proc ot_pg_native_birth_end {} {incr ::end_calls;return $::counters}
if {![catch {ot_pg_place_canary_finish global_place} why] || ![string match *native_callback_not_verified_inactive* $why]} {error FALSE_ACTIVE_PASS}
''',
 'skipped_io_only':'''close $::ot_pgc::fh;set ::ot_pgc::fh {};set ::ot_pgc::started 0;set ::ot_pgc::active 0
if {[dict get [ot_pg_place_canary_finish io_placement] state] ne "SKIPPED_NATIVE_BODY"} {error IO_SKIP}
if {![catch {ot_pg_place_canary_finish resize} why]} {error FALSE_SKIPPED_STAGE}
'''
}
with tempfile.TemporaryDirectory(prefix='source_controls_',dir=R)as d:
 d=Path(d)
 for name,body in CASES.items():
  log=d/(name+'.jsonl');h=d/(name+'.tcl')
  h.write_text(BASE.replace('@COMMON@',str(COMMON)).replace('@HELPER@',str(R/'pg_place_canary.tcl')).replace('@LOG@',str(log))+body+'\nputs SOURCE_ONLY_PASS\n')
  p=subprocess.run(['tclsh',str(h)],capture_output=True,text=True)
  assert p.returncode==0 and p.stdout.strip().endswith('SOURCE_ONLY_PASS'),(name,p.stdout,p.stderr)
  rows=[json.loads(s)for s in log.read_text().splitlines()]
  if name=='requested_plain_separate_port':
   enters=[r for r in rows if r['kind']=='ENTER'];leaves=[r for r in rows if r['kind']=='LEAVE']
   assert next(r for r in enters if r['tag']=='GPL_REQUESTED')['timing_arg']=='1'
   assert next(r for r in enters if r['tag']=='GPL_NATIVE')['timing_arg']=='0'
   assert next(r for r in leaves if r['tag']=='BUFFER_PORTS')['delta_creates']=='2'
   assert next(r for r in leaves if r['tag']=='GPL_NATIVE')['delta_creates']=='3'
  if name=='real_error_preserved_for_fallback':
   native=[r for r in rows if r['kind']=='LEAVE'and r['tag']=='GPL_NATIVE']
   assert [r['command_code']for r in native]==['1','0']
  print('SOURCE_ONLY_CONTROL_PASS',name)
print('NO_NATIVE_QUALIFICATION_FROM_THESE_CONTROLS')
