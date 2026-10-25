uplevel #0 {source /work/mscts_core.tcl}
set_propagated_clock [all_clocks]
estimate_parasitics -global_routing
global_route -start_incremental
repair_design -slew_margin 40 -cap_margin 20 -max_wire_length 80
detailed_placement
check_placement -verbose
global_route -end_incremental
uplevel #0 {ot_ms_balance grt}
estimate_parasitics -global_routing
puts "F57N_GRT [ot_ms_report grt]"
write_guides $::env(RESULTS_DIR)/route.guide
