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

set block [[[ord::get_db] getChip] getBlock]
puts "OT_INSTALLED_INVENTORY"
foreach inst [$block getInsts] {
 set mn [[$inst getMaster] getName]
 set name [$inst getName]
 if {$mn eq "ot_hbm_accel_tc16" || $mn eq "ot_hbm_accel_bd_col"} {
  foreach t [$inst getITerms] {
   if {[$t getIoType] ne "OUTPUT"} {continue}
   set net [$t getNet]
   puts "MACRO_OUT $name/[[$t getMTerm] getName] NET=[$net getName]"
   foreach q [$net getITerms] {
    set qi [$q getInst]
    puts "LOAD [$qi getName]/[[$q getMTerm] getName] MASTER=[[$qi getMaster] getName] DIR=[$q getIoType] XY=[$qi getLocation]"
   }
  }
 }
 if {[string match {g_new.g_l2s[0].g_h[0].g_c[0].u_leaf/*} $name]} {
  puts "REP_INST $name $mn"
 }
}
set nq 0
foreach net [$block getNets] {
 set name [string map {\\ ""} [$net getName]]
 if {[string first {g_new.g_l2s[0].g_h[0].g_c[0].u_leaf/} $name] == 0 && [regexp {/(ibf|bov|gv|gf|gy|gt)} $name]} {
  puts "CONTROL_NET $name"
  foreach t [$net getITerms] {puts "CONTROL_PIN [[$t getInst] getName]/[[$t getMTerm] getName] [[$t getInst] getMaster] [$t getIoType]"}
  incr nq
 }
 if {[regexp {h_start|h_pop|g_pq} $name]} {puts "PRODUCTION_NAME $name"}
}
puts "OT_CONTROL_NET_COUNT $nq"
set starts {}
foreach pattern {*/g_hardk.u_tc/y* */g_hardk.u_tc/otag* */g_hardk.u_tc/ov */g_hardk.u_tc/fault */g_hbdk.u_bd/y* */g_hbdk.u_bd/otag* */g_hbdk.u_bd/ov */g_hbdk.u_bd/fault} {
 set pts [get_pins -hierarchical $pattern]
 puts "OT_MACRO_PATTERN $pattern COUNT=[llength $pts]"
 set starts [concat $starts $pts]
}
puts "OT_REPRESENTATIVE_NET_LOADS"
foreach pat {*u_leaf/bov *u_leaf/ibf} {
 set nets [get_nets -hierarchical $pat]
 puts "OT_NET_PATTERN $pat COUNT=[llength $nets]"
 if {[llength $nets]} {report_net -connections -digits 6 [lindex $nets 0]}
}
puts "OT_MACRO_TO_G1"
puts "OT_MACRO_TIMING_RETAINED_IN_DETAIL_LOG"
set g1 {}
foreach pat {*u_leaf/gy*/CLK *u_leaf/gt*/CLK *u_leaf/gv*/CLK *u_leaf/gf*/CLK} {set g1 [concat $g1 [get_pins -hierarchical $pat]]}
set dg [concat [get_pins -hierarchical *u_gd*/D] [get_pins -hierarchical *u_gv*/D]]
puts "OT_G1_CLOCK_COUNT [llength $g1] OT_DG_D_COUNT [llength $dg]"
puts "OT_G1_TO_DG"
report_checks -from $g1 -to $dg -path_delay max -group_path_count 2 -format full_clock_expanded -fields {slew cap fanout}
puts "OT_DETAIL_COMPLETE"
exit
