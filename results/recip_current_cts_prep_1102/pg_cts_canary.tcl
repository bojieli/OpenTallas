# PRIVATE RECIP ordinary CTS source proposal. Definitions only until begin after load.
# No production strict-CTS admission, flag edits, algorithm choice, or target run.
namespace eval ::ot_ctsc {
  variable started 0; variable active 0; variable stage {}; variable fh {}
  variable watches {}; variable stack {}; variable serial 0
  variable failed {}; variable final {}; variable initial {}; variable phase BODY
}
proc ot_pg_cts_canary_log {kind fields} {
  if {$::ot_ctsc::fh eq ""} {return}
  set line "\{\"kind\":[ot_pg_json_string $kind],\"stage\":[ot_pg_json_string $::ot_ctsc::stage]"
  dict for {key value} $fields {
    append line "," [ot_pg_json_string $key] ":" [ot_pg_json_string $value]
  }
  append line "\}"
  puts $::ot_ctsc::fh $line; flush $::ot_ctsc::fh
  puts "PG_CTS_CANARY $line"
}
proc ot_pg_cts_canary_begin {stage} {
  if {$::ot_ctsc::started} {error PG_CTS_CANARY_DOUBLE_BEGIN}
  if {$stage ni {cts}} {error PG_CTS_CANARY_BAD_STAGE}
  # Actual reviewed manual121 environment is UNSET, not strict1 weakened to0.
  if {[info exists ::env(OT_PG_STRICT)]} {error PG_CTS_CANARY_ORIGINAL_UNSET_MODE_CHANGED}
  foreach {path want} {
    /work/pg_native_qualified_562.tcl e19c5fd9872e37f68d610e2dc46608359c9970b7c9e6de84f546f3b3c3ea3a2d
    /work/pg_native_8c9.so 8c9e1eef9ec6451a5bc1710da15fe683785aa8791d21099e4ee9ec30fee0a93b
  } {
    if {[lindex [exec sha256sum -- $path] 0] ne $want} {error "PG_CTS_CANARY_BAD_DEPENDENCY $path"}
  }
  source /work/pg_native_qualified_562.tcl
  ot_pg_native_birth_begin /work/pg_native_8c9.so
  set ::ot_ctsc::started 1; set ::ot_ctsc::active 1; set ::ot_ctsc::stage $stage
  foreach command {repair_clock_inverters clock_tree_synthesis} {
    if {[ot_pg_native_birth_supported $command]} {error "PG_CTS_CANARY_MUST_NOT_ADMIT_STRICT_CTS $command"}
  }
  set ::ot_ctsc::fh [open /work/PG_CTS_CANARY_${stage}.jsonl {WRONLY CREAT EXCL}]
  set ::ot_ctsc::initial [ot_native_pg_audit]
  ot_pg_cts_canary_log BEGIN [dict create strict_original UNSET strict_cts_supported 0 native $::ot_ctsc::initial]
}
proc ot_pg_cts_canary_enter {tag command op} {
  if {!$::ot_ctsc::active} {error PG_CTS_CANARY_CALLBACK_INACTIVE}
  set before [ot_native_pg_audit]
  set id [incr ::ot_ctsc::serial]
  lappend ::ot_ctsc::stack [list $id $tag $command $before]
  set fields [dict create id $id tag $tag phase $::ot_ctsc::phase argv $command native_before $before]
  if {$tag in {CTS_NATIVE CTS_REQUESTED}} {
    dict set fields sink_clustering_arg [expr {[lsearch -exact $command -sink_clustering_enable] >= 0}]
    dict set fields repair_clock_nets_arg [expr {[lsearch -exact $command -repair_clock_nets] >= 0}]
  }
  ot_pg_cts_canary_log ENTER $fields
}
proc ot_pg_cts_canary_leave {tag command code result op} {
  if {![llength $::ot_ctsc::stack]} {
    if {$code == 0} {error PG_CTS_CANARY_MISSING_ENTER}
    return
  }
  lassign [lindex $::ot_ctsc::stack end] id prior_tag argv before
  set ::ot_ctsc::stack [lrange $::ot_ctsc::stack 0 end-1]
  if {$tag ne $prior_tag} {error PG_CTS_CANARY_NESTED_TRACE_MISMATCH}
  set audit_code [catch {ot_native_pg_audit} after]
  set fields [dict create id $id tag $tag phase $::ot_ctsc::phase argv $argv command_code $code result $result]
  if {!$audit_code} {
    dict set fields native_after $after
    foreach field {creates swaps bound} {dict set fields delta_$field [expr {[dict get $after $field]-[dict get $before $field]}]}
  } else {dict set fields native_audit_error $after}
  set log_code [catch {ot_pg_cts_canary_log LEAVE $fields} log_error]
  # Preserve a real native failure/fallback code; never hide it with trace errors.
  if {$audit_code} {
    puts stderr "PG_CTS_CANARY_ORIGINAL_COMPLETION code=$code result=$result"
    # Abort on a PG defect even if the original failure was a retryable GPL0305.
    error "PG_CTS_CANARY_POSTCALL_PG_REFUSED $after"
  }
  if {$code != 0} {
    if {$log_code} {puts stderr "PG_CTS_CANARY_FAILED_CALL_LOG $log_error"}
    return
  }
  if {$log_code} {error $log_error}
}
proc ot_pg_cts_canary_after_pre {stage} {
  if {!$::ot_ctsc::active || $stage ne $::ot_ctsc::stage} {error PG_CTS_CANARY_BAD_PRE_BOUNDARY}
  set now [ot_native_pg_audit]
  ot_pg_cts_canary_log PRE_HOOK [dict create native_before $::ot_ctsc::initial native_after $now]
  # Attach after the complete original PRE. The MM macro wrapper must remain.
  if {[info commands ::ot_mcc_cts_orig] eq ""} {error PG_CTS_CANARY_FROZEN_MACRO_WRAPPER_MISSING}
  ot_pg_cts_canary_log WATCHES [dict create requested_command ::clock_tree_synthesis final_command ::ot_mcc_cts_orig]
  set operations [list CLOCK_INVERTERS ::repair_clock_inverters CTS_REQUESTED ::clock_tree_synthesis CTS_NATIVE ::ot_mcc_cts_orig REPAIR_DESIGN ::repair_design REPAIR_TIMING ::repair_timing]
  foreach {tag command} $operations {
    if {[info commands $command] eq ""} continue
    trace add execution $command enter [list ot_pg_cts_canary_enter $tag]
    lappend ::ot_ctsc::watches [list $command enter [list ot_pg_cts_canary_enter $tag]]
    trace add execution $command leave [list ot_pg_cts_canary_leave $tag]
    lappend ::ot_ctsc::watches [list $command leave [list ot_pg_cts_canary_leave $tag]]
  }
}
proc ot_pg_cts_canary_finish {stage} {
  if {!$::ot_ctsc::started} {
    error PG_CTS_CANARY_BEGIN_NOT_REACHED
  }
  if {$stage ne $::ot_ctsc::stage} {error PG_CTS_CANARY_STAGE_MISMATCH}
  if {!$::ot_ctsc::active} {
    if {$::ot_ctsc::failed ne ""} {error "PG_CTS_CANARY_PRIOR_FINISH_FAILED $::ot_ctsc::failed"}
    return [dict create state ALREADY_FINISHED stage $stage native $::ot_ctsc::final]
  }
  set failures {}
  foreach rec $::ot_ctsc::watches {
    lassign $rec command op callback
    if {[catch {trace remove execution $command $op $callback} why]} {lappend failures $why}
  }
  set ::ot_ctsc::watches {}
  if {[llength $::ot_ctsc::stack]} {lappend failures PG_CTS_CANARY_UNFINISHED_CALL_STACK}
  set end_code [catch {ot_pg_native_birth_end} receipt end_options]
  set ::ot_ctsc::active 0
  if {$end_code != 0} {lappend failures "native_end_code=$end_code $receipt"}
  set status_code [catch {ot_native_pg_status} status]
  if {$status_code != 0 || ![dict exists $status active] || [dict get $status active]} {lappend failures "native_callback_not_verified_inactive $status"}
  if {[catch {ot_pg_cts_canary_log END [dict create native $receipt native_status_after_end $status cleanup_errors $failures]} why]} {lappend failures $why}
  if {$::ot_ctsc::fh ne ""} {
    if {[catch {close $::ot_ctsc::fh} why]} {lappend failures $why}
    set ::ot_ctsc::fh {}
  }
  if {[llength $failures]} {
    set ::ot_ctsc::failed $failures
    error "PG_CTS_CANARY_FINISH_FAILED $failures"
  }
  set ::ot_ctsc::final $receipt
  return [dict create state FINISHED stage $stage native $receipt]
}

proc ot_pg_cts_canary_before_post {stage} {
  if {!$::ot_ctsc::active || $stage ne $::ot_ctsc::stage} {error PG_CTS_CANARY_BAD_POST_BOUNDARY}
  ot_pg_cts_canary_log BEFORE_POST [dict create native [ot_native_pg_audit]]
  set ::ot_ctsc::phase POST
}
