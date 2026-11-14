# GENERATED-COPY of tools/die_plan/grt_post.tcl (POST_GLOBAL_ROUTE hook, FLOW 2026-10-25): density kits' GRT-RC tap
# pass (tap_balance_grt.tcl, OT_TAP_GRT_MODE), then the IO virtual clock back to the kit SDC (TT) value so 5_1_grt.sdc
# and every later stage carry constraint.sdc unchanged.
set gq_dir [file dirname [file normalize [info script]]]
# FLOW-PGCAP-1 11-13: the PG-TRACK-TRUTH obstructions (grt_pre.tcl) come off first: 5_1_grt.odb, DRT and sign-off
# see the kit geometry unchanged.
if {[llength [info procs ot_pgtt_remove]]} { ot_pgtt_remove }
if {[info exists ::env(OT_TAP_GRT_MODE)] && $::env(OT_TAP_GRT_MODE) ne ""} { source [file join $gq_dir tap_balance_grt.tcl] }
if {[info exists ::env(OT_VCLK_CORNER)] && $::env(OT_VCLK_CORNER) eq "ff"} { ot_vclk_bind tt }
# DIE-HBM-97 11-09 HOPLATCH-HOLD: the GRT-repair-only hop latch -hold uncertainty (grt_pre.tcl) comes off before the SDC is written
if {[info exists ::ot_hlh_pins] && [llength $::ot_hlh_pins]} {
  foreach ot_hlh_p $::ot_hlh_pins { unset_clock_uncertainty -hold $ot_hlh_p }
  puts "OT_HOP_LATCH_HOLD removed from [llength $::ot_hlh_pins] hop latch clock pins"
  set ::ot_hlh_pins {}
}
# Repair buffers do not replace registered reset stations or waive their reach.
if {[info exists ::env(OT_RESET_PAIR_FIXED)] && $::env(OT_RESET_PAIR_FIXED) eq "1"} {
  uplevel #0 [list source [file join $gq_dir reset_pair_place.tcl]]
  ot_reset_pair_verify_hops [ord::get_db_block] 405
}
# CTS/GRT timing repair creates cells after floorplan PG assignment. Apply the
# persisted global-connect rules to those cells (protected ones included, pg_connect.tcl) before writing this
# checkpoint, then the hard check (OT_PG_OPEN fails the GRT step).
uplevel #0 [list source [file join $gq_dir pg_connect.tcl]]
ot_pg_connect_all grt_post
ot_pg_require_bound grt_post
# VSN6-B 11-11 S7: loud non-tap cell census against the 400k run cap (cell_census.tcl, ADVISORY)
if {[file exists [file join $gq_dir cell_census.tcl]]} {
  uplevel #0 [list source [file join $gq_dir cell_census.tcl]]; ot_cell_census grt
} else { puts "OT_CELL_CENSUS WARN stage=grt: cell_census.tcl is not in the kit, no recount" }
