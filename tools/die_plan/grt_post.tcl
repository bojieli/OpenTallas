# GENERATED-COPY of tools/die_plan/grt_post.tcl (POST_GLOBAL_ROUTE hook, FLOW 2026-10-25): density kits' GRT-RC tap
# pass (tap_balance_grt.tcl, OT_TAP_GRT_MODE), then the IO virtual clock back to the kit SDC (TT) value so 5_1_grt.sdc
# and every later stage carry constraint.sdc unchanged.
set gq_dir [file dirname [file normalize [info script]]]
if {[info exists ::env(OT_TAP_GRT_MODE)] && $::env(OT_TAP_GRT_MODE) ne ""} { source [file join $gq_dir tap_balance_grt.tcl] }
if {[info exists ::env(OT_VCLK_CORNER)] && $::env(OT_VCLK_CORNER) eq "ff"} { ot_vclk_bind tt }
# CTS/GRT timing repair creates cells after floorplan PG assignment. Apply the
# persisted global-connect rules to those cells (protected ones included, pg_connect.tcl) before writing this
# checkpoint, then the hard check (OT_PG_OPEN fails the GRT step).
uplevel #0 [list source [file join $gq_dir pg_connect.tcl]]
ot_pg_connect_all grt_post
ot_pg_require_bound grt_post
