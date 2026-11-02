from pathlib import Path
import subprocess
import pytest

HELPER=Path(__file__).parents[2]/'physical/common_flow/native_pg_binding.tcl'

@pytest.mark.parametrize('mode', ['begin_trace_failure','end_trace_failure','end_audit_and_trace_failure'])
def test_native_transaction_uninstalls_after_partial_trace_failures(tmp_path,mode):
    harness=tmp_path/'cleanup.tcl'
    harness.write_text('''source {@HELPER@}
set ::uninstalled 0
set ::installed_guards 0
set ::removed {}
namespace eval ord {}
proc ord::get_db_block {} {return block}
proc block {method} {if {$method eq "getDataBase"} {return db}; return 2}
proc db {method} {return 1}
proc ot_pg_install_unsupported_birth_guards {} {incr ::installed_guards}
proc ot_pg_prepare {args} {return model}
proc ot_pg_assert_all_native {args} {}
proc ot_native_pg_install {args} {}
proc ot_native_pg_uninstall {} {incr ::uninstalled}
proc ot_native_pg_audit {} {if {$::mode eq "end_audit_and_trace_failure"} {error PRIMARY_AUDIT}; return {creates 0}}
rename load original_load
proc load {args} {}
proc read_db {args} {}
proc read_def {args} {}
rename trace original_trace
proc trace {action kind command args} {
 if {$action eq "add" && $command eq "::read_def"} {error TRACE_ADD_FAILURE}
 if {$action eq "remove"} {
  lappend ::removed $command
  if {$::mode ne "begin_trace_failure" && $command eq "::read_db"} {error TRACE_REMOVE_FAILURE}
 }
}
set ::mode @MODE@
if {$::mode eq "begin_trace_failure"} {
 set code [catch {ot_pg_native_birth_begin module.so} message]
 if {$::installed_guards != 1 || $message ne "TRACE_ADD_FAILURE" || $::removed ne "::read_db"} {error "begin mismatch $message $::removed"}
} else {
 set ::ot_pg_birth_traced {::read_db ::read_def}
 set code [catch {ot_pg_native_birth_end} message]
 if {$::removed ne "::read_db ::read_def"} {error "failed to attempt all removals"}
 if {$::mode eq "end_audit_and_trace_failure" && $message ne "PRIMARY_AUDIT"} {error "lost primary error $message"}
 if {$::mode eq "end_trace_failure" && ![string match OT_PG_BIRTH_CLEANUP_FAILED* $message]} {error "lost cleanup error $message"}
}
if {$code != 1 || $::uninstalled != 1 || [info exists ::ot_pg_birth_traced]} {error "unwind incomplete $code $::uninstalled"}
puts PASS
'''.replace('@HELPER@',str(HELPER)).replace('@MODE@',mode))
    r=subprocess.run(['tclsh',str(harness)],text=True,capture_output=True)
    assert r.returncode==0 and r.stdout.strip().endswith('PASS'),r.stdout+r.stderr

@pytest.mark.parametrize('kind',['coroutine','ensemble','object','missing_introspector'])
def test_tcl_command_standins_never_grant_native_capability(tmp_path,kind):
    harness=tmp_path/'standin.tcl'
    harness.write_text('''source {@HELPER@}
namespace eval ord {}
proc ord::get_db_block {} {return block}
proc block {method} {return db}
proc db {method} {return 1}
set ::fake_status {contract native_pg_birth.flat_literal.v1 active 1 database_id 1 block_id 1}
proc fake_status {} {return $::fake_status}
proc fake_audit {} {}
set kind @KIND@
switch $kind {
 coroutine {
  coroutine ot_native_pg_status apply {{} {while {1} {yield $::fake_status}}}
  coroutine ot_native_pg_audit apply {{} {while {1} {yield {}}}}
 }
 ensemble {
  namespace ensemble create -command ::ot_native_pg_status -map {status fake_status}
  namespace ensemble create -command ::ot_native_pg_audit -map {audit fake_audit}
 }
 object {
  oo::object create ot_native_pg_status
  oo::object create ot_native_pg_audit
 }
 missing_introspector {
  rename ::tcl::unsupported::corotype {}
  interp alias {} ot_native_pg_status {} fake_status
  interp alias {} ot_native_pg_audit {} fake_audit
 }
}
if {[ot_pg_native_birth_supported repair_design] || [ot_pg_native_birth_supported repair_timing] || [ot_pg_native_birth_supported filler_placement]} {error "fake capability admitted $kind"}
puts PASS
'''.replace('@HELPER@',str(HELPER)).replace('@KIND@',kind))
    r=subprocess.run(['tclsh',str(harness)],text=True,capture_output=True)
    assert r.returncode==0 and r.stdout.strip()=='PASS',r.stdout+r.stderr
