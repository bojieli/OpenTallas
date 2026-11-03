# PRIVATE121 ordinary PLACE experiment. Definitions only until begin after load.
# No production strict-GPL admission, flag edits, algorithm choice, or target run.
namespace eval ::ot_pgc {
  variable started 0; variable active 0; variable stage {}; variable fh {}
  variable watches {}; variable stack {}; variable serial 0
  variable failed {}; variable final {}; variable initial {}
}
proc ot_pg_place_canary_log {kind fields} {
  if {$::ot_pgc::fh eq ""} {return}
  set line "\{\"kind\":[ot_pg_json_string $kind],\"stage\":[ot_pg_json_string $::ot_pgc::stage]"
  dict for {key value} $fields {
    append line "," [ot_pg_json_string $key] ":" [ot_pg_json_string $value]
  }
  append line "\}"
  puts $::ot_pgc::fh $line; flush $::ot_pgc::fh
  puts "PG_PLACE_CANARY $line"
}
proc ot_pg_place_canary_begin {stage} {
  if {$::ot_pgc::started} {error PG_PLACE_CANARY_DOUBLE_BEGIN}
  if {$stage ni {global_place_skip_io io_placement global_place resize detail_place}} {error PG_PLACE_CANARY_BAD_STAGE}
  # Actual reviewed manual121 environment is UNSET, not strict1 weakened to0.
  if {[info exists ::env(OT_PG_STRICT)]} {error PG_PLACE_CANARY_ORIGINAL_UNSET_MODE_CHANGED}
  foreach {path want} {
    /work/pg_native_qualified_562.tcl e19c5fd9872e37f68d610e2dc46608359c9970b7c9e6de84f546f3b3c3ea3a2d
    /work/pg_native_8c9.so 8c9e1eef9ec6451a5bc1710da15fe683785aa8791d21099e4ee9ec30fee0a93b
  } {
    if {[lindex [exec sha256sum -- $path] 0] ne $want} {error "PG_PLACE_CANARY_BAD_DEPENDENCY $path"}
  }
  source /work/pg_native_qualified_562.tcl
  ot_pg_native_birth_begin /work/pg_native_8c9.so
  set ::ot_pgc::started 1; set ::ot_pgc::active 1; set ::ot_pgc::stage $stage
  if {[ot_pg_native_birth_supported global_placement]} {error PG_PLACE_CANARY_MUST_NOT_ADMIT_GLOBAL_STRICT_GPL}
  set ::ot_pgc::fh [open /work/PG_PLACE_CANARY_${stage}.jsonl {WRONLY CREAT EXCL}]
  set ::ot_pgc::initial [ot_native_pg_audit]
  ot_pg_place_canary_log BEGIN [dict create strict_original UNSET strict_gpl_supported 0 native $::ot_pgc::initial]
}
proc ot_pg_place_canary_enter {tag command op} {
  if {!$::ot_pgc::active} {error PG_PLACE_CANARY_CALLBACK_INACTIVE}
  set before [ot_native_pg_audit]
  set id [incr ::ot_pgc::serial]
  lappend ::ot_pgc::stack [list $id $tag $command $before]
  set fields [dict create id $id tag $tag argv $command native_before $before]
  if {$tag in {GPL_NATIVE GPL_REQUESTED}} {
    dict set fields timing_arg [expr {[lsearch -exact $command -timing_driven] >= 0}]
    dict set fields routability_arg [expr {[lsearch -exact $command -routability_driven] >= 0}]
    dict set fields skip_io_arg [expr {[lsearch -exact $command -skip_io] >= 0}]
  }
  ot_pg_place_canary_log ENTER $fields
}
proc ot_pg_place_canary_leave {tag command code result op} {
  if {![llength $::ot_pgc::stack]} {
    if {$code == 0} {error PG_PLACE_CANARY_MISSING_ENTER}
    return
  }
  lassign [lindex $::ot_pgc::stack end] id prior_tag argv before
  set ::ot_pgc::stack [lrange $::ot_pgc::stack 0 end-1]
  if {$tag ne $prior_tag} {error PG_PLACE_CANARY_NESTED_TRACE_MISMATCH}
  set audit_code [catch {ot_native_pg_audit} after]
  set fields [dict create id $id tag $tag argv $argv command_code $code result $result]
  if {!$audit_code} {
    dict set fields native_after $after
    foreach field {creates swaps bound} {dict set fields delta_$field [expr {[dict get $after $field]-[dict get $before $field]}]}
  } else {dict set fields native_audit_error $after}
  set log_code [catch {ot_pg_place_canary_log LEAVE $fields} log_error]
  # Preserve a real native failure/fallback code; never hide it with trace errors.
  if {$audit_code} {
    puts stderr "PG_PLACE_CANARY_ORIGINAL_COMPLETION code=$code result=$result"
    # Abort on a PG defect even if the original failure was a retryable GPL0305.
    error "PG_PLACE_CANARY_POSTCALL_PG_REFUSED $after"
  }
  if {$code != 0} {
    if {$log_code} {puts stderr "PG_PLACE_CANARY_FAILED_CALL_LOG $log_error"}
    return
  }
  if {$log_code} {error $log_error}
}
proc ot_pg_place_canary_after_pre {stage} {
  if {!$::ot_pgc::active || $stage ne $::ot_pgc::stage} {error PG_PLACE_CANARY_BAD_PRE_BOUNDARY}
  set now [ot_native_pg_audit]
  ot_pg_place_canary_log PRE_HOOK [dict create native_before $::ot_pgc::initial native_after $now]
  # Attach AFTER original PRE: face_flops has completed its rename/guard setup.
  # Trace final original API and tag outer requested arguments separately.
  set gpl ::global_placement
  if {[info commands ::ot_gpl_native] ne ""} {set gpl ::ot_gpl_native}
  ot_pg_place_canary_log WATCHES [dict create requested_command ::global_placement final_command $gpl]
  set operations [list GPL_NATIVE $gpl]
  if {$gpl ne "::global_placement"} {lappend operations GPL_REQUESTED ::global_placement}
  lappend operations BUFFER_PORTS ::buffer_ports REMOVE_BUFFERS ::remove_buffers REPAIR_DESIGN ::repair_design REPAIR_TIMING ::repair_timing CLUSTER_FLOPS ::cluster_flops REPLACE_ARITH ::replace_arith_modules
  foreach {tag command} $operations {
    if {[info commands $command] eq ""} continue
    trace add execution $command enter [list ot_pg_place_canary_enter $tag]
    lappend ::ot_pgc::watches [list $command enter [list ot_pg_place_canary_enter $tag]]
    trace add execution $command leave [list ot_pg_place_canary_leave $tag]
    lappend ::ot_pgc::watches [list $command leave [list ot_pg_place_canary_leave $tag]]
  }
}
proc ot_pg_place_canary_finish {stage} {
  if {!$::ot_pgc::started} {
    if {$stage eq "io_placement"} {return [dict create state SKIPPED_NATIVE_BODY stage $stage]}
    error PG_PLACE_CANARY_BEGIN_NOT_REACHED
  }
  if {$stage ne $::ot_pgc::stage} {error PG_PLACE_CANARY_STAGE_MISMATCH}
  if {!$::ot_pgc::active} {
    if {$::ot_pgc::failed ne ""} {error "PG_PLACE_CANARY_PRIOR_FINISH_FAILED $::ot_pgc::failed"}
    return [dict create state ALREADY_FINISHED stage $stage native $::ot_pgc::final]
  }
  set failures {}
  foreach rec $::ot_pgc::watches {
    lassign $rec command op callback
    if {[catch {trace remove execution $command $op $callback} why]} {lappend failures $why}
  }
  set ::ot_pgc::watches {}
  if {[llength $::ot_pgc::stack]} {lappend failures PG_PLACE_CANARY_UNFINISHED_CALL_STACK}
  set end_code [catch {ot_pg_native_birth_end} receipt end_options]
  set ::ot_pgc::active 0
  if {$end_code != 0} {lappend failures "native_end_code=$end_code $receipt"}
  set status_code [catch {ot_native_pg_status} status]
  if {$status_code != 0 || ![dict exists $status active] || [dict get $status active]} {lappend failures "native_callback_not_verified_inactive $status"}
  if {[catch {ot_pg_place_canary_log END [dict create native $receipt native_status_after_end $status cleanup_errors $failures]} why]} {lappend failures $why}
  if {$::ot_pgc::fh ne ""} {
    if {[catch {close $::ot_pgc::fh} why]} {lappend failures $why}
    set ::ot_pgc::fh {}
  }
  if {[llength $failures]} {
    set ::ot_pgc::failed $failures
    error "PG_PLACE_CANARY_FINISH_FAILED $failures"
  }
  set ::ot_pgc::final $receipt
  return [dict create state FINISHED stage $stage native $receipt]
}
