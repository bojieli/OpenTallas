# PATH-QC-SRAMIF 10-25: post-legalisation residual passes (repair -> DPL -> incremental GRT -> re-estimate, max 2 more,
# same margin): the single pass left -2.4..-5.9 ps on 8-24 EP after DPL moved buffers in the anchored IF columns.
for {set s6_p 2} {$s6_p <= 3 && [sta::endpoint_violation_count min] > 0} {incr s6_p} {
  puts "S6_HOLD_PASS $s6_p start [s6_ps [sta::worst_slack_cmd min]] ep [sta::endpoint_violation_count min]"
  repair_timing -hold -hold_margin $s6_m -max_buffer_percent [expr {[info exists ::env(OT_S6_MAXBUF)] ? $::env(OT_S6_MAXBUF) : 30}]
  global_route -start_incremental
  detailed_placement
  check_placement -verbose
  global_route -end_incremental
  estimate_parasitics -global_routing
}
