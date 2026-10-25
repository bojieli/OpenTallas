# QC rp1-clock 10-25 POST_GLOBAL_ROUTE hook (SKIP_INCREMENTAL_REPAIR=1): leaf balance again on GRT RC (codex
# clock_grt pattern), then data DRV repair (kit post_grt_drv pattern) and -- phase 2 only (OT_GRT_HOLD=1, SDC vclk
# latency already = the core's measured I) -- in-flow hold repair at HOLD_SLACK_MARGIN (0..5 ps).  Clock nets are
# never touched by repair_design / repair_timing.  Guides rewritten for detailed route.
set ::env(CQB_GRT) 1
set ::env(CQB_TAG) cqbgrt
source /work/clock_leaf_balance.tcl
set_propagated_clock [all_clocks]
estimate_parasitics -global_routing
global_route -start_incremental
repair_design -slew_margin 40 -cap_margin 20
if {[info exists ::env(OT_GRT_HOLD)] && $::env(OT_GRT_HOLD)} {
  if {$::env(HOLD_SLACK_MARGIN) > 5} { error "RP1 recipe: in-flow hold margin must be 0..5 ps" }
  puts "RP1_GRT repair_timing -hold -hold_margin $::env(HOLD_SLACK_MARGIN)"
  repair_timing -hold -hold_margin $::env(HOLD_SLACK_MARGIN) -max_buffer_percent 100
}
detailed_placement
check_placement -verbose
global_route -end_incremental
estimate_parasitics -global_routing
set rp_sv NA; catch {set rp_sv [sta::max_slew_violation_count]}
puts [format "RP1_GRT hold_wns %.2f hold_endpoints %d setup_wns %.2f slew_viol %s" [expr {[sta::worst_slack_cmd min]*1e12}] [sta::endpoint_violation_count min] [expr {[sta::worst_slack_cmd max]*1e12}] $rp_sv]
write_guides $::env(RESULTS_DIR)/route.guide
