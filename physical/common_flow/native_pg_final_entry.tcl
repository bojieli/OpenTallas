# Strict PRE_FINAL_REPORT entry (S81-CAPC3 10-19, S81.STA.PG): bind unprotected cell births, then the strict guard.
#
# Why (measured, s81sl_capc2-s81capc2-174c61fc3 6_report): the strict guard refused 565196 PG terminals (first input464
# BUFx2 VDD). Strict mode binds PG only at the protection sites (bind-before-dont_touch); every UNPROTECTED cell born
# after the PDN-time global_connect (buffer_ports input/output buffers, resizer repair buffers, CTS cells that are not
# protected, filler cells) is bound in stock ORFS only by final_connect.tcl's global_connect, which runs AFTER this hook.
# The strict guard runs BEFORE it, so every strict route refused at 6_report (no strict route had ever reached it).
#
# Fix: in the final_connect process -- load_design 6_1_fill.odb, no parasitics estimated or read yet (setRC only sets
# layer RC values; final extraction and sign-off STA run after this hook) -- bind every unprotected cell's PG MTerms to
# its native rule net with the same explicit binder the protection sites use (master-driven census, preflight, verify).
# PG ITerm binding changes no signal net, wire or placement, so the route-time timing stands. This is the earliest point
# after the last cell birth (fillcell) whose database is carried to 6_final.odb (POST_FILLCELL runs after its write;
# PRE_DENSITY_FILL output is discarded when USE_FILL=0).
# NOT exempted: a PROTECTED (dont_touch) cell with an unbound PG MTerm is refused here by name (global_connect skips
# dont_touch insts, dbGlobalConnect.cpp:163 -- that is the defect behind the 3732 unbound CAPC terms, and its only fix is
# bind-before-protect at the protection site). Wrong domain / missing ITerm / ambiguous rule refuse as in the binder.
# The unchanged strict guard and the 6_final write guard then assert every native PG terminal (no exemptions).
if {[info exists ::env(OT_PG_STRICT)] && $::env(OT_PG_STRICT) eq "1"} {
  set ot_pg_helper [file join [file dirname [info script]] native_pg_binding.tcl]
  if {[info exists ::env(OT_PG_HELPER)]} {set ot_pg_helper $::env(OT_PG_HELPER)} elseif {![file exists $ot_pg_helper]} {set ot_pg_helper /src/physical/common_flow/native_pg_binding.tcl}
  source $ot_pg_helper
  set ot_pg_fe_block [ord::get_db_block]
  if {([info exists ::ot_pg_bindings_dirty] && $::ot_pg_bindings_dirty > 0) || ([info exists ::ot_pg_spef_seen] && $::ot_pg_spef_seen)} {
    error "OT_PG_FINAL_ENTRY_STATE_REFUSED (bindings changed or SPEF read before the final entry)"
  }
  set ot_pg_fe_map [ot_pg_prepare $ot_pg_fe_block]
  set ot_pg_fe_protected {}; set ot_pg_fe_insts 0; set ot_pg_fe_terms 0
  set ot_pg_fe_dirty0 [expr {[info exists ::ot_pg_bindings_dirty] ? $::ot_pg_bindings_dirty : 0}]
  foreach ot_pg_fe_inst [$ot_pg_fe_block getInsts] {
    set ot_pg_fe_open 0
    foreach ot_pg_fe_row [ot_pg_master_census $ot_pg_fe_inst] {
      lassign $ot_pg_fe_row ot_pg_fe_mt ot_pg_fe_term ot_pg_fe_why
      if {$ot_pg_fe_why ne "" || [$ot_pg_fe_term getNet] eq "NULL"} {set ot_pg_fe_open 1; break}
    }
    if {!$ot_pg_fe_open} continue
    if {[$ot_pg_fe_inst isDoNotTouch]} {lappend ot_pg_fe_protected [$ot_pg_fe_inst getName]; continue}
    # Preflight (missing ITerm / wrong domain / unknown rule) refuses inside the binder before any connect.
    incr ot_pg_fe_terms [ot_pg_bind_before_protect $ot_pg_fe_map $ot_pg_fe_inst]
    incr ot_pg_fe_insts
  }
  if {[llength $ot_pg_fe_protected]} {
    error "OT_PG_FINAL_PROTECTED_UNBOUND_REFUSED count=[llength $ot_pg_fe_protected] first=[lrange $ot_pg_fe_protected 0 4]"
  }
  # The binder counts its connects as RC-dirty for in-flow (post-estimate) protection sites. Here no parasitics exist
  # yet in this process (checked above), so the births are pre-extraction: restore the counter for the guard.
  set ::ot_pg_bindings_dirty $ot_pg_fe_dirty0
  puts "OT_PG_FINAL_BIRTH_BIND unprotected_insts=$ot_pg_fe_insts terms=$ot_pg_fe_terms protected_unbound=0"
  unset ot_pg_fe_map
}
# ORFS copies step hooks into the job's hook directory under another name: fall back to the shipped source tree.
set ot_pg_fe_boot [file join [file dirname [info script]] native_pg_bootstrap.tcl]
if {![file exists $ot_pg_fe_boot]} {set ot_pg_fe_boot /src/physical/common_flow/native_pg_bootstrap.tcl}
source $ot_pg_fe_boot
