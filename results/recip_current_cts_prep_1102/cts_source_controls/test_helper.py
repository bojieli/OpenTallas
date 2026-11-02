"""Source-only instrumentation controls; no native CTS or PG qualification."""
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
set ::ot_ctsc::started 1;set ::ot_ctsc::active 1;set ::ot_ctsc::stage cts
set ::ot_ctsc::fh [open {@LOG@} w];set ::ot_ctsc::initial $::counters
'''
CASES={
 'inverter_CTS_and_POST_separate':'''proc repair_clock_inverters {} {return ZERO}
proc ot_mcc_cts_orig {args} {add_births 3;return OK}
proc clock_tree_synthesis {args} {ot_mcc_cts_orig {*}$args}
proc repair_timing {args} {add_births 2}
ot_pg_cts_canary_after_pre cts
repair_clock_inverters
clock_tree_synthesis -sink_clustering_enable -repair_clock_nets
ot_pg_cts_canary_before_post cts
repair_timing -setup
if {[dict get [ot_pg_cts_canary_finish cts] state] ne "FINISHED"} {error END}
if {[dict get [ot_pg_cts_canary_finish cts] state] ne "ALREADY_FINISHED" || $::end_calls!=1} {error IDEMPOTENCE}
if {[trace info execution ot_mcc_cts_orig] ne "" || [trace info execution clock_tree_synthesis] ne ""} {error TRACE_LEAK}
''',
 'ordinary_tool_error_preserved':'''proc ot_mcc_cts_orig {args} {error ORDINARY_CTS_ERROR}
proc clock_tree_synthesis {args} {ot_mcc_cts_orig {*}$args}
ot_pg_cts_canary_after_pre cts
if {![catch {clock_tree_synthesis -sink_clustering_enable} why] || $why ne "ORDINARY_CTS_ERROR"} {error LOST_NATIVE_ERROR}
ot_pg_cts_canary_finish cts
''',
 'PG_error_is_fatal':'''proc ot_mcc_cts_orig {args} {set ::audit_bad 1;error ORIGINAL_CTS_ERROR}
proc clock_tree_synthesis {args} {ot_mcc_cts_orig {*}$args}
ot_pg_cts_canary_after_pre cts
if {![catch {clock_tree_synthesis} why] || ![string match PG_CTS_CANARY_POSTCALL_PG_REFUSED* $why]} {error LOST_PG_ERROR}
set ::audit_bad 0
ot_pg_cts_canary_finish cts
''',
 'cleanup_failure_stays_failed':'''set ::end_error 1
if {![catch {ot_pg_cts_canary_finish cts} why]} {error FALSE_CLEANUP_PASS}
if {![catch {ot_pg_cts_canary_finish cts} why] || $::end_calls!=1} {error FALSE_SECOND_PASS}
''',
 'status_must_be_inactive':'''proc ot_pg_native_birth_end {} {incr ::end_calls;return $::counters}
if {![catch {ot_pg_cts_canary_finish cts} why] || ![string match *native_callback_not_verified_inactive* $why]} {error FALSE_ACTIVE_PASS}
''',
 'no_uninitialized_skip':'''close $::ot_ctsc::fh;set ::ot_ctsc::fh {};set ::ot_ctsc::started 0;set ::ot_ctsc::active 0
if {![catch {ot_pg_cts_canary_finish cts} why] || $why ne "PG_CTS_CANARY_BEGIN_NOT_REACHED"} {error FALSE_SKIP}
'''}
with tempfile.TemporaryDirectory(dir=R)as td:
 d=Path(td)
 for name,body in CASES.items():
  log=d/(name+'.jsonl');h=d/(name+'.tcl')
  h.write_text(BASE.replace('@COMMON@',str(COMMON)).replace('@HELPER@',str(R/'pg_cts_canary.tcl')).replace('@LOG@',str(log))+body+'\nputs SOURCE_ONLY_PASS\n')
  p=subprocess.run(['tclsh',str(h)],capture_output=True,text=True)
  assert p.returncode==0 and p.stdout.strip().endswith('SOURCE_ONLY_PASS'),(name,p.stdout,p.stderr)
  rows=[json.loads(s)for s in log.read_text().splitlines()]
  if name=='inverter_CTS_and_POST_separate':
   leaves=[x for x in rows if x['kind']=='LEAVE']
   assert next(x for x in leaves if x['tag']=='CLOCK_INVERTERS')['delta_creates']=='0'
   assert next(x for x in leaves if x['tag']=='CTS_NATIVE')['delta_creates']=='3'
   assert next(x for x in leaves if x['tag']=='REPAIR_TIMING')['phase']=='POST'
   assert next(x for x in leaves if x['tag']=='REPAIR_TIMING')['delta_creates']=='2'
  print('SOURCE_ONLY_CONTROL_PASS',name)
print('NO_NATIVE_QUALIFICATION_FROM_THESE_CONTROLS')
