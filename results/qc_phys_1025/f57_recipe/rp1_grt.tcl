# QC-RP1 10-25 POST_GLOBAL_ROUTE (SKIP_INCREMENTAL_REPAIR=1): (F2 RC calibration is in grt_pre.tcl) F5 tap/macro-leaf re-balance on the
# calibrated GRT RC, data DRV repair, and -- route phase only (OT_GRT_HOLD=1, SDC vclk latency = the core's measured I)
# in-flow hold repair at HOLD_SLACK_MARGIN (0..5 ps).  Clock nets are never touched by repair_design / repair_timing.
puts "OT_RC_CAL applied in PRE_GLOBAL_ROUTE (grt_pre.tcl)"
set ::env(OT_CTAP_EST) grt
set ::env(OT_CTAP_TAG) ctpgrt
source /work/core_taps_post.tcl
set_propagated_clock [all_clocks]
estimate_parasitics -global_routing
# QC-PHYS f57 pass 2: time every tap cell at estimate + the measured f56c RCX correction (per ORFS corner tc / bc), so
# the hold repair and the reported hold see routed-basis skew between taps (macros share their tap -> covered)
if {[info exists ::env(OT_CTAP_CORR)] && $::env(OT_CTAP_CORR) ne ""} {
  source $::env(OT_CTAP_CORR)
  puts "OT_CTAP_ASSIGN taps tc [ot_ctap_assign $ot_ctap_corr 0 tc max] bc [ot_ctap_assign $ot_ctap_corr 1 bc min]"
}
global_route -start_incremental
repair_design -slew_margin 40 -cap_margin 20 -max_wire_length [expr {[info exists ::env(OT_MAX_WIRE_UM)] ? $::env(OT_MAX_WIRE_UM) : 80}]
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
