# HELD normal fillcell adapter. Admission is checked BEFORE the first factory.
proc ot_pg_fill_verify_hook_bindings {} {
  foreach {key expected} {PRE_FILLCELL_TCL /work/pg_fill_pre.tcl POST_FILLCELL_TCL /work/pg_fill_post.tcl} {
    if {![info exists ::env($key)] || $::env($key) ne $expected} {error "OT_PG_FILL_EXACT_HOOK_REQUIRED $key"}
  }
}
proc ot_pg_fill_enter_guard {command op} {
  ot_pg_fill_verify_hook_bindings
  foreach flag {ot_pg_fill_pre_complete ot_pg_fill_baseline_ready} {
    if {![info exists ::$flag] || [set ::$flag] ne "1"} {error "OT_PG_FILL_PRE_BASELINE_REQUIRED $flag"}
  }
  if {[info commands ot_pg_strict_enabled] eq "" || ![ot_pg_strict_enabled] ||
      [info commands ot_pg_native_birth_supported] eq "" ||
      ![ot_pg_native_birth_supported filler_placement]} {
    error OT_PG_FILL_REAL_NATIVE_CURRENT_DB_PG0_REQUIRED
  }
  puts "OT_PG_FILL_BEFORE_FACTORY_NATIVE_ADMITTED $command"
}
if {![info exists ::env(FILL_CELLS)] || [string trim $::env(FILL_CELLS)] eq ""} {error OT_PG_FILL_REQUIRES_EXPLICIT_MASTERS}
ot_pg_fill_verify_hook_bindings
unset -nocomplain ::ot_pg_fill_post_reached ::ot_pg_fill_pre_complete ::ot_pg_fill_baseline_ready
if {[info commands ::filler_placement] eq ""} {error OT_PG_FILL_NATIVE_COMMAND_MISSING}
# Execution traces follow a command through the canonical strict-guard rename.
trace add execution ::filler_placement enter ::ot_pg_fill_enter_guard
set ot_pg_fill_code [catch {
  source $::env(SCRIPTS_DIR)/fillcell.native_pg_original.tcl
} ot_pg_fill_result ot_pg_fill_options]
set ot_pg_fill_failures {}
foreach command {::filler_placement ::ot_pg_unsupported_filler_placement} {
  if {[info commands $command] ne ""} {
    if {[catch {trace remove execution $command enter ::ot_pg_fill_enter_guard} why]} {lappend ot_pg_fill_failures $why}
  }
}
# Always attempt native cleanup, even when the status query itself fails.
if {[info commands ot_native_pg_status] ne ""} {
  set status_code [catch {
    set status [ot_native_pg_status]
    if {![dict exists $status active]} {error "OT_PG_FILL_STATUS_MALFORMED $status"}
  } status_result]
  if {$status_code} {
    lappend ot_pg_fill_failures "OT_PG_FILL_STATUS_FAILED $status_result"
    if {[info commands ot_pg_native_birth_cleanup] ne ""} {
      if {[catch {ot_pg_native_birth_cleanup} why]} {lappend ot_pg_fill_failures $why}
    } elseif {[info commands ot_native_pg_uninstall] ne ""} {
      if {[catch {ot_native_pg_uninstall} why]} {lappend ot_pg_fill_failures $why}
    }
  } elseif {[dict get $status active]} {
    set end_code [catch {ot_pg_native_birth_end} why]
    if {$end_code} {lappend ot_pg_fill_failures "OT_PG_FILL_END_FAILED code=$end_code $why"}
  }
  if {[catch {
    set status [ot_native_pg_status]
    if {![dict exists $status active] || [dict get $status active]} {error "OT_PG_FILL_CALLBACK_STILL_ACTIVE $status"}
    puts "OT_PG_FILL_CALLBACK_FINAL $status"
  } why]} {lappend ot_pg_fill_failures $why}
} elseif {$ot_pg_fill_code == 0} {
  lappend ot_pg_fill_failures OT_PG_FILL_STATUS_MISSING
}
if {$ot_pg_fill_code == 1} {
  if {[llength $ot_pg_fill_failures]} {puts stderr "OT_PG_FILL_CLEANUP_REFUSED $ot_pg_fill_failures"}
  return -options $ot_pg_fill_options $ot_pg_fill_result
}
if {[llength $ot_pg_fill_failures]} {error "OT_PG_FILL_CLEANUP_REFUSED $ot_pg_fill_failures"}
if {$ot_pg_fill_code != 0} {error "OT_PG_FILL_NONLOCAL_BODY_REFUSED code=$ot_pg_fill_code result=$ot_pg_fill_result"}
if {![info exists ::ot_pg_fill_post_reached] || !$::ot_pg_fill_post_reached} {error OT_PG_FILL_FULL_POST_NOT_REACHED}
