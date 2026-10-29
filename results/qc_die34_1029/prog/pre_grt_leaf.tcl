# DIE-QC-34 PROG ONE route, PRE_GLOBAL_ROUTE: normal leaf repair for the 354 moved clock sinks (GEOM-58 cond. 2): the
# standard resizer clock-net repair (as ORFS CTS runs it), legalise, then PG bind of any new cell + hard 0-open check.
# No clock ECO: no tree edits, no trims/pads, no skew targets.
set_propagated_clock [all_clocks]
estimate_parasitics -placement
set n0 [sta::network_leaf_instance_count]
puts "LEAF_PRE max_slew_viol [sta::max_slew_violation_count] max_cap_viol [sta::max_capacitance_violation_count]"
repair_clock_nets
detailed_placement
check_placement
puts "LEAF_REPAIR repair_clock_nets leaf instances $n0 -> [sta::network_leaf_instance_count]"
source /work/pg_connect.tcl
ot_pg_connect_all pre_grt_leaf
ot_pg_require_bound pre_grt_leaf
report_clock_skew -setup
