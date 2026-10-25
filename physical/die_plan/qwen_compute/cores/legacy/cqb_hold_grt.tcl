# Small FF hold closure only, on the already-balanced physical clock tree.
# run_cqb_route.sh selects native FF libs; TT setup is independently signed.
set_propagated_clock [all_clocks]
estimate_parasitics -global_routing
set cqb_hold_before [sta::time_sta_ui [sta::worst_slack_cmd min]]
set cqb_hold_ep [sta::endpoint_violation_count min]
puts "CQB_HOLD_BEFORE $cqb_hold_before endpoints$cqb_hold_ep"
if {$cqb_hold_before < -100.0 || $cqb_hold_ep > 2000} {
  error "CQB structural FF hold failure: stop before DRT (owner 00:46 rule)"
}
set_max_fanout 24 [current_design]
global_route -start_incremental
repair_timing -hold -hold_margin 5 -allow_setup_violations -max_buffer_percent 40
detailed_placement
global_route -end_incremental
estimate_parasitics -global_routing
set cqb_hold_after [sta::time_sta_ui [sta::worst_slack_cmd min]]
set cqb_hold_ep [sta::endpoint_violation_count min]
puts "CQB_HOLD_AFTER $cqb_hold_after endpoints$cqb_hold_ep"
if {$cqb_hold_after < 0.0 || $cqb_hold_ep > 0} {
  error "CQB FF hold not closed on real GRT RC: no DRT"
}
write_guides $::env(RESULTS_DIR)/route.guide
