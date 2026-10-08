# CLAUDE WFC src r19 step 2: SS-corner max slew / cap repair (repair_design) after the FF hold ECO, on the global-routed db
set P /OpenROAD-flow-scripts/flow/platforms/asap7
set M /src/physical/asap7_memory_macros_v2/ot_sram_1r1w_512x128_m4_r2c2
set_thread_count 8
read_lef $P/lef/asap7_tech_1x_201209.lef
read_lef $P/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_lef $M/ot_sram_1r1w_512x128_m4_r2c2.lef
foreach f [lsort [glob $P/lib/NLDM/*_RVT_SS_*.lib*]] { read_liberty $f }
read_liberty $M/ot_sram_1r1w_512x128_m4_r2c2_ss.lib
read_db /out/5_1_grt.odb
read_sdc /eco/signoff.sdc
set_propagated_clock [all_clocks]
source $P/setRC.tcl
set_dont_use {*x1p*_ASAP7* *xp*_ASAP7* SDF* ICG*}
set_global_routing_layer_adjustment M2-M7 0.25
set_routing_layers -clock M4-M7
set_routing_layers -signal M2-M7
estimate_parasitics -global_routing
puts "OT_DRV pre"; report_check_types -max_slew -max_capacitance -violators; report_worst_slack -max -digits 2
global_route -start_incremental
repair_design -slew_margin 30 -cap_margin 20
detailed_placement
check_placement -verbose
global_route -end_incremental
estimate_parasitics -global_routing
puts "OT_DRV post"; report_check_types -max_slew -max_capacitance -violators; report_worst_slack -max -digits 2
write_db /out/5_1_grt.odb
puts "OT_DRV done"
