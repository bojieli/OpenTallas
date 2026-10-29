# DIE-QC-34 PROG ONE route, POST_GLOBAL_ROUTE: PG bind of the GRT-stage repair cells + hard 0-open check; GRT congestion
# (>= 50 iterations, overflow 0 incl. the W column) is enforced by ORFS global_route (congestion -> error, no DRT).
source /work/pg_connect.tcl
ot_pg_connect_all post_grt
ot_pg_require_bound post_grt
report_clock_skew -setup
puts "POST_GRT setup [sta::worst_slack_cmd max] hold [sta::worst_slack_cmd min] slew_viol [sta::max_slew_violation_count]"
