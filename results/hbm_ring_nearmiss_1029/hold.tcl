source $::env(SCRIPTS_DIR)/load.tcl
load_design eco_grt.odb 4_cts.sdc
set_propagated_clock [all_clocks]
set_routing_layers -signal M2-M5 -clock M2-M5
set_global_routing_layer_adjustment * 0.25
global_route -congestion_iterations 50 -congestion_report_file /out/hold_congestion.rpt
estimate_parasitics -global_routing
ot_mm_sync
global_route -start_incremental
ot_repair_timing {-hold -hold_margin 5 -setup_margin 0}
detailed_placement
check_placement -verbose
global_route -end_incremental -resistance_aware
estimate_parasitics -global_routing
ot_mm_sync
report_checks -path_delay max -group_path_count 4 -format full_clock_expanded -fields {slew cap fanout} > /out/hold_setup.rpt
report_checks -path_delay min -group_path_count 4 -format full_clock_expanded -fields {slew cap fanout} > /out/hold_hold.rpt
report_worst_slack -max
report_worst_slack -min
write_db /out/hold_grt.odb
write_verilog /out/eco.v
exit
