source /work/cf/mscts_core.tcl
set_propagated_clock [all_clocks]
estimate_parasitics -global_routing
global_route -start_incremental
repair_design -slew_margin 40 -cap_margin 20 -max_wire_length [expr {[info exists ::env(OT_MAX_WIRE_UM)] ? $::env(OT_MAX_WIRE_UM) : 80}]
detailed_placement
global_route -end_incremental
ot_ms_balance grt
