# GENERATED-COPY of tools/die_plan/cts_post.tcl (POST_CTS hook, FLOW 2026-10-25): tap trees balanced to the bound
# insertion (tap_balance.tcl), then register pairs with no logic between them moved onto one clock leaf
# (leaf_affinity.tcl, F4; OT_LEAF_AFFINITY=0 turns it off).
# ORFS sources POST_CTS inside a procedure. Both helpers define global procs
# whose state must live at global scope too.
set cp_dir [file dirname [file normalize [info script]]]
uplevel #0 [list source [file join $cp_dir tap_balance.tcl]]
if {![info exists ::env(OT_LEAF_AFFINITY)] || $::env(OT_LEAF_AFFINITY) ne "0"} { uplevel #0 [list source [file join $cp_dir leaf_affinity.tcl]] }
# S81 AM half-cycle correction, opt-in and guarded by the baseline affinity checks.
if {[info exists ::env(OT_S81_RCK_AM_COHORT)] && $::env(OT_S81_RCK_AM_COHORT) eq "1"} { uplevel #0 [list source [file join $cp_dir rck_am_cohort.tcl]] }
# S81 rck depth balance (INV-pair pads, span acceptance), opt-in, after the leaf-repeat hook and the tap balance.
if {[info exists ::env(OT_S81_RCK_BALANCE)] && $::env(OT_S81_RCK_BALANCE) eq "1"} { uplevel #0 [list source [file join $cp_dir rck_balance.tcl]] }
# The GPL placement helper is loaded as a library in this fresh CTS process;
# report every actual root14 tail without moving any post-DPL register.
if {[info exists ::env(OT_SERDES_RM_LOCAL)] && $::env(OT_SERDES_RM_LOCAL) eq "1"} {
 set ::env(OT_SERDES_RM_LOCAL) 0
 uplevel #0 [list source [file join $cp_dir serdes_rm_local.tcl]]
 set ::env(OT_SERDES_RM_LOCAL) 1
 uplevel #0 {ot_rm_local::visibility clk_t14}
}
# KV-Q2-CLK-1115 (opt-in, OT_CTS_TAP_CENTROID=1): branch buffers to the centre of their loads (cts_tap_centroid.tcl)
if {[info exists ::env(OT_CTS_TAP_CENTROID)] && $::env(OT_CTS_TAP_CENTROID) eq "1" && [file exists [file join $cp_dir cts_tap_centroid.tcl]]} { uplevel #0 [list source [file join $cp_dir cts_tap_centroid.tcl]] }
# Optional reset FF/driver pairs must retain the registered405um reach after CTS.
if {[info exists ::env(OT_RESET_PAIR_FIXED)] && $::env(OT_RESET_PAIR_FIXED) eq "1"} {
  uplevel #0 [list source [file join $cp_dir reset_pair_place.tcl]]
  ot_reset_pair_verify_hops [ord::get_db_block] 405
}
# WAVE-FLOW-R2 11-17 (COORD lever 6): per-tap insertion after the tap balance, ADVISORY (OT_TAP_INSERTION lines; never an edit, never a gate)
if {[file exists [file join $cp_dir tap_insertion.tcl]]} { uplevel #0 [list source [file join $cp_dir tap_insertion.tcl]] }
# FLOW 2026-10-26 PG: every clock/pad/leaf cell created up to here gets its supplies before 4_1_cts.odb is written
# (global_connect skips dont_touch cells: s8b ot_ms_* spine buffers), then a hard check (OT_PG_OPEN fails CTS).
uplevel #0 [list source [file join $cp_dir pg_connect.tcl]]
ot_pg_connect_all cts_post
ot_pg_require_bound cts_post
# FWDCLK-1: stop the kit here when a forwarded clock output lost its driver in CTS (generated per kit by gen_phys).
if {[file exists [file join $cp_dir landing_export_check.tcl]]} { uplevel #0 [list source [file join $cp_dir landing_export_check.tcl]] }
# VSN6-B 11-11 S7: loud non-tap cell census against the 400k run cap (cell_census.tcl, ADVISORY)
if {[file exists [file join $cp_dir cell_census.tcl]]} {
  uplevel #0 [list source [file join $cp_dir cell_census.tcl]]; ot_cell_census cts
} else { puts "OT_CELL_CENSUS WARN stage=cts: cell_census.tcl is not in the kit, no recount" }
# CTS-POST-RPT-1 11-19: CTS-stage timing on the post-hook netlist (4_cts_final.rpt is written before this hook)
if {[file exists [file join $cp_dir cts_post_report.tcl]]} { uplevel #0 [list source [file join $cp_dir cts_post_report.tcl]] }
