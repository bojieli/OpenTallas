# DSROM q-element POST_GLOBAL_ROUTE hold ECO (2026-10-05, QX = 10 routes Z18c/Z18d): routed FF hold missed by 1-11 ps on
# 3 endpoints whose capture clock leaf slowed 15-30 ps between the global-route estimate and the extracted route, while a
# flow-wide HOLD_SLACK_MARGIN above 25 ps fails at CTS (RSZ-0060, max buffer count; Z16a-c, Z18e-j).  This hook adds a
# second hold pass at global-route parasitics with a larger repair TARGET (OT_ECO_HOLD_MARGIN, library units = ps) and a
# larger buffer budget, then re-legalises and incrementally re-routes the changed nets.  Constraints (SDC, 60 / 25 ps
# uncertainty, corners) are unchanged; the hook only over-fixes.  Setup is protected by -setup_margin (SETUP_SLACK_MARGIN).
set m [expr {[info exists ::env(OT_ECO_HOLD_MARGIN)] ? $::env(OT_ECO_HOLD_MARGIN) : 45}]
set sm [expr {[info exists ::env(SETUP_SLACK_MARGIN)] ? $::env(SETUP_SLACK_MARGIN) : 0}]
puts "OT_ECO_HOLD start margin=$m setup_margin=$sm"
estimate_parasitics -global_routing
puts "OT_ECO_HOLD pre worst_hold=[sta::worst_slack -min] worst_setup=[sta::worst_slack -max]"
global_route -start_incremental
if {[catch {repair_timing -hold -hold_margin $m -setup_margin $sm -max_buffer_percent 40 -verbose} err]} {
  puts "OT_ECO_HOLD repair_timing caught: $err"
}
detailed_placement
check_placement -verbose
global_route -end_incremental -congestion_report_file $::env(REPORTS_DIR)/congestion_post_hold_eco.rpt
estimate_parasitics -global_routing
puts "OT_ECO_HOLD post worst_hold=[sta::worst_slack -min] worst_setup=[sta::worst_slack -max]"
write_guides $::env(RESULTS_DIR)/route.guide
