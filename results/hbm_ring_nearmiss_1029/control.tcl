source $::env(SCRIPTS_DIR)/load.tcl
load_design 5_1_grt.odb 4_cts.sdc
set_propagated_clock [all_clocks]
set block [ord::get_db_block]
detailed_placement
check_placement -verbose
set_routing_layers -signal M2-M5 -clock M2-M5
set_global_routing_layer_adjustment * 0.25
global_route -congestion_iterations 50 -congestion_report_file /out/control_congestion.rpt
estimate_parasitics -global_routing
ot_mm_sync
report_checks -path_delay max -group_path_count 4 -format full_clock_expanded -fields {slew cap fanout} > /out/control_setup.rpt
report_checks -path_delay min -group_path_count 4 -format full_clock_expanded -fields {slew cap fanout} > /out/control_hold.rpt
report_worst_slack -max
report_worst_slack -min
write_db /out/control_grt.odb
write_verilog /out/eco.v
exit
