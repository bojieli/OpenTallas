read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_lef /src/physical/hbm_accel_sm_views/ot_hbm_accel_tc16/ot_hbm_accel_tc16.lef
read_lef /src/physical/hbm_accel_sm_views/ot_hbm_accel_bd_col/ot_hbm_accel_bd_col.lef
read_lef /src/physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.lef
read_lef /src/physical/hbm_accel_macros/ot_sram_1r1w_512x256_m1_r2c2/ot_sram_1r1w_512x256_m1_r2c2.lef
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_SS_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_SS_nldm_220122.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_SS_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_SS_nldm_220123.lib
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_SS_nldm_211120.lib.gz
read_liberty /src/physical/hbm_accel_sm_views/ot_hbm_accel_tc16/ot_hbm_accel_tc16_ss.lib
read_liberty /src/physical/hbm_accel_sm_views/ot_hbm_accel_bd_col/ot_hbm_accel_bd_col_ss.lib
read_liberty /src/physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2_ss.lib
read_liberty /src/physical/hbm_accel_macros/ot_sram_1r1w_512x256_m1_r2c2/ot_sram_1r1w_512x256_m1_r2c2_ss.lib
read_db /retained/results/asap7/opentallas_ot_hbm_accel_sm_v_asap7_fsm_sm_r2/base/4_cts.odb
read_sdc /retained/results/asap7/opentallas_ot_hbm_accel_sm_v_asap7_fsm_sm_r2/base/4_cts.sdc
source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl
estimate_parasitics -placement
set_propagated_clock [all_clocks]
puts "OT_INVENTORY_BEGIN"
set block [[ord::get_db] getChip]
set block [$block getBlock]
set nn 0
foreach n [$block getNets] {
 set name [$n getName]
 if {[regexp {g_new\.g_l2s\[0\]\.g_h\[0\]\.g_c\[0\]\.(bov|fov|ibf|gy\[|gt\[|gv|gf)} $name]} {
  puts "NET $name"
  foreach t [$n getITerms] {puts "ITERM [[$t getInst] getName]/[[$t getMTerm] getName] [[$t getInst] getMaster] [$t getIoType]"}
  incr nn
 }
}
puts "OT_NET_COUNT $nn"
set mp [get_pins -hierarchical */g_hardk.u_tc/ov]
puts "OT_TC_OV_COUNT [llength $mp]"
report_checks -from $mp -path_delay max -group_path_count 2 -format full_clock_expanded -fields {slew cap fanout}
set bp [get_pins -hierarchical */g_hbdk.u_bd/ov]
puts "OT_BD_OV_COUNT [llength $bp]"
report_checks -from $bp -path_delay max -group_path_count 2 -format full_clock_expanded -fields {slew cap fanout}
puts "OT_QUERY_COMPLETE"
exit
