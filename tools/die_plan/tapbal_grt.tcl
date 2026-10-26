# GENERATED-COPY of tools/die_plan/tapbal_grt.tcl (FLOW-INFRA-2 2026-10-25): GRT-RC tap pre-pass, run by run_kit.sh
# between 'make cts' and the FF-only 'make grt' as  make run RUN_SCRIPT=/work/tapbal_grt.tcl CORNER=TC CORNERS=tc.
# Why here and not POST_GLOBAL_ROUTE: ORFS global_route.tcl runs repair_timing (the FF hold repair) BEFORE it sources
# POST_GLOBAL_ROUTE, so delay cells added there land after the hold buffers were sized against the unbalanced tree.
# The post-CTS pass (tap_balance.tcl, POST_CTS) balances on the placement estimate; the pre-route insertion gate
# (postcts_gate.tcl) reads the GRT estimate (the basis the RCX calibration was fitted on).  Canaries 10-25 showed the
# two estimates differ by -14..+8 ps per design on the calibrated RC (FLOW INSERTION 08:21).  This pass: global route
# the CTS database on the kit's own layer settings (persisted in the ODB since floorplan), estimate GRT parasitics,
# run tap_balance.tcl again with OT_TAP_EST=grt (its edits are wrapped in global_route -start/-end_incremental and
# legalised), and write 4_cts.odb back (the placement-balanced database is kept as 4_cts_plc.odb).  The full GRT step
# then routes and hold-repairs on the balanced tree; postcts_gate.tcl checks TT and FF after it.
# Env: OT_TAP_TARGET_PS (TT bound, kit config), OT_TAP_GRT_PRE_ITERS (GRT congestion iterations, default 30).
source $::env(SCRIPTS_DIR)/load.tcl
load_design 4_cts.odb 4_cts.sdc
set tg_dir [file dirname [file normalize [info script]]]
set_propagated_clock [all_clocks]
set tg_it [expr {[info exists ::env(OT_TAP_GRT_PRE_ITERS)] ? $::env(OT_TAP_GRT_PRE_ITERS) : 30}]
set tg_args [list -congestion_iterations $tg_it -allow_congestion]
if {[info exists ::env(GLOBAL_ROUTE_ARGS)] && $::env(GLOBAL_ROUTE_ARGS) ne ""} {
  # the kit's GRT options, minus the two this pass sets itself (-congestion_iterations N, -allow_congestion)
  set tg_ga $::env(GLOBAL_ROUTE_ARGS)
  for {set i 0} {$i < [llength $tg_ga]} {incr i} {
    set a [lindex $tg_ga $i]
    if {$a eq "-congestion_iterations"} { incr i; continue }
    if {$a eq "-allow_congestion"} continue
    lappend tg_args $a
  }
}
# as ORFS global_route.tcl: -resistance_aware when the platform/kit enables it (the FF GRT step routes the clock nets
# that way; without it this pass read the pin-register clock ~14 ps later than the post-GRT gate, head + KV 10-25)
set ::ot_grt_res_aware ""
if {[llength [info commands append_env_var]]} { append_env_var ::ot_grt_res_aware ENABLE_RESISTANCE_AWARE -resistance_aware 0 }
set tg_args [concat $tg_args $::ot_grt_res_aware]
puts "OT_TAP_GRT_PRE global_route $tg_args"
global_route {*}$tg_args
estimate_parasitics -global_routing
set ::env(OT_TAP_EST) grt
set ::env(OT_TAP_TAG) p
set ::env(OT_TAP_REPORT_ONLY) 0
source [file join $tg_dir tap_balance.tcl]
puts "OT_TAP_GRT_PRE rebalance: $::tb_added delay cells on GRT RC (target $::tb_target ps TT)"
# PROTOTYPE (OT_PINREG_PAD=1): pad only the pin-register leaf groups to the bound pin-register insertion
if {[info exists ::env(OT_PINREG_PAD)] && $::env(OT_PINREG_PAD)} { source [file join $tg_dir pinreg_pad.tcl] }
# measure again on the GRT estimate of the edited tree (report only), so the log shows the residual the gate will see
if {$::tb_added > 0} {
  estimate_parasitics -global_routing
  set ::env(OT_TAP_REPORT_ONLY) 1
  source [file join $tg_dir tap_balance.tcl]
}
check_placement
file copy -force $::env(RESULTS_DIR)/4_cts.odb $::env(RESULTS_DIR)/4_cts_plc.odb
write_db $::env(RESULTS_DIR)/4_cts.odb
puts "OT_TAP_GRT_PRE done: 4_cts.odb rewritten (placement-balanced copy 4_cts_plc.odb)"
