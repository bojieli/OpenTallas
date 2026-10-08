# CLAUDE WFC src r18: FF-corner hold repair under the region IO SDC on the GLOBAL-ROUTED design (5_1_grt.odb), before
# detailed route, so the normal ORFS 5_2 detailed route / fill / finish follow (no detailed wire is ever broken).
set P /OpenROAD-flow-scripts/flow/platforms/asap7
set M /src/physical/asap7_memory_macros_v2/ot_sram_1r1w_512x128_m4_r2c2
set_thread_count 8
read_lef $P/lef/asap7_tech_1x_201209.lef
read_lef $P/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_lef $M/ot_sram_1r1w_512x128_m4_r2c2.lef
foreach f [lsort [glob $P/lib/NLDM/*_RVT_FF_*.lib*]] { read_liberty $f }
read_liberty $M/ot_sram_1r1w_512x128_m4_r2c2_ff.lib
read_db /in/5_1_grt.odb
read_sdc /eco/signoff.sdc
set_propagated_clock [all_clocks]
source /eco/region_ff.sdc
source $P/setRC.tcl
set_dont_use {*x1p*_ASAP7* *xp*_ASAP7* SDF* ICG*}
set_global_routing_layer_adjustment M2-M7 0.25
set_routing_layers -clock M4-M7
set_routing_layers -signal M2-M7
estimate_parasitics -global_routing
puts "OT_ECO pre"; report_worst_slack -min -digits 2; report_worst_slack -max -digits 2
global_route -start_incremental
set n0 [llength [get_cells *]]
if {[catch {repair_timing -hold -hold_margin $::env(OT_HOLD_MARGIN) -setup_margin $::env(OT_SETUP_MARGIN) -max_buffer_percent 10 -verbose} err]} { puts "OT_ECO repair_timing caught: $err" }
puts "OT_ECO cells_added [expr {[llength [get_cells *]] - $n0}]"
detailed_placement
check_placement -verbose
global_route -end_incremental
estimate_parasitics -global_routing
puts "OT_ECO post"; report_worst_slack -min -digits 2; report_worst_slack -max -digits 2
write_db /out/5_1_grt.odb
puts "OT_ECO done"
