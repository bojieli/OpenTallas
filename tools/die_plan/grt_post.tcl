# GENERATED-COPY of tools/die_plan/grt_post.tcl (POST_GLOBAL_ROUTE hook, FLOW 2026-10-25): density kits' GRT-RC tap
# pass (tap_balance_grt.tcl, OT_TAP_GRT_MODE), then the IO virtual clock back to the kit SDC (TT) value so 5_1_grt.sdc
# and every later stage carry constraint.sdc unchanged.
set gq_dir [file dirname [file normalize [info script]]]
if {[info exists ::env(OT_TAP_GRT_MODE)] && $::env(OT_TAP_GRT_MODE) ne ""} { source [file join $gq_dir tap_balance_grt.tcl] }
if {[info exists ::env(OT_VCLK_CORNER)] && $::env(OT_VCLK_CORNER) eq "ff"} { ot_vclk_bind tt }
# Repair buffers do not replace registered reset stations or waive their reach.
if {[info exists ::env(OT_RESET_PAIR_FIXED)] && $::env(OT_RESET_PAIR_FIXED) eq "1"} {
  uplevel #0 [list source [file join $gq_dir reset_pair_place.tcl]]
  ot_reset_pair_verify_hops [ord::get_db_block] 405
}
# CTS/GRT timing repair creates cells after floorplan PG assignment. Apply the
# persisted global-connect rules to those cells before writing this checkpoint.
global_connect
