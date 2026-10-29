# HBM-CORES-KITS-10 ring V1 (data-only ECO): Codex pad1v2 GRT placement + strap_qid ECO, clock cells FIRM (tree unchanged);
# DRV repair with slew/cap margins (the 186 routed slew nets, RCX ~1.8x setRC) + FF hold repair margin 15 (routed RCX loss ~9.7 ps).
source $::env(SCRIPTS_DIR)/load.tcl
load_design 5_1_grt_strap.odb 4_cts.sdc
set_propagated_clock [all_clocks]
set block [ord::get_db_block]
set nf 0
foreach i [$block getInsts] { if {[string match {clkbuf_*} [$i getName]] || [string match {mp_isl*} [$i getName]]} { if {[$i getPlacementStatus] ne "FIRM"} {$i setPlacementStatus FIRM}; incr nf } }
puts "OT_FROZEN_CLOCK_CELLS $nf"
set_routing_layers -signal M2-M5 -clock M2-M5
set_global_routing_layer_adjustment * 0.25
global_route -congestion_iterations 50 -congestion_report_file /out/v1_congestion.rpt
estimate_parasitics -global_routing
ot_mm_unsync
global_route -start_incremental
repair_design -slew_margin 50 -cap_margin 20
ot_mm_sync
ot_repair_timing {-hold -hold_margin 15 -setup_margin 0}
ot_mm_unsync
detailed_placement
check_placement -verbose
global_route -end_incremental -resistance_aware
estimate_parasitics -global_routing
ot_mm_unsync
ot_mm_sync
report_checks -path_delay max -group_path_count 4 -format full_clock_expanded -fields {slew cap fanout} > /out/v1_setup.rpt
report_checks -path_delay min -group_path_count 4 -format full_clock_expanded -fields {slew cap fanout} > /out/v1_hold.rpt
report_worst_slack -max
report_worst_slack -min
ot_mm_unsync
report_check_types -max_slew -max_capacitance -violators > /out/v1_drv.rpt
write_db $::env(RESULTS_DIR)/5_1_grt.odb
exit
