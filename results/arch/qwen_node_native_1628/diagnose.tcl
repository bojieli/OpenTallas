read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_TT_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_TT_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_TT_nldm_211120.lib.gz
read_db /work/results/asap7/opentallas_ot_qwen_tile_node_asap7_ref_ot_qwen_tile_node_r5_78b36aae5/base/6_final.odb
read_sdc /work/results/asap7/opentallas_ot_qwen_tile_node_asap7_ref_ot_qwen_tile_node_r5_78b36aae5/base/6_final.sdc
read_spef /work/results/asap7/opentallas_ot_qwen_tile_node_asap7_ref_ot_qwen_tile_node_r5_78b36aae5/base/6_final.spef
set_propagated_clock [all_clocks]
read_sdc /work/w18_extra.sdc
read_sdc /meas/app0_io_ref_routed.sdc
puts "OT_WS max [sta::worst_slack_cmd max] min [sta::worst_slack_cmd min]"
report_checks -to [all_outputs] -path_delay max -group_path_count 12 -fields {slew cap fanout input nets} -format full_clock_expanded
puts "NODE_OUTPUT_DRIVER_CHAINS"
set block [ord::get_db_block]
foreach name {y[0] y[100] y[511] t_out[0] t_out[100] t_out[511] vy fault} {
 set bt [$block findBTerm $name]
 puts "PIN $name"
 if {$bt == "NULL"} {continue}
 set net [$bt getNet]
 for {set k 0} {$k < 8} {incr k} {
  set drivers {}
  foreach it [$net getITerms] {if {[$it getIoType] == "OUTPUT"} {lappend drivers $it}}
  if {[llength $drivers] != 1} {break}
  set it [lindex $drivers 0]; set inst [$it getInst]
  puts "DRIVER [$inst getName] [[$inst getMaster] getName] [$inst getLocation] net=[$net getName]"
  set inputs {}
  foreach ip [$inst getITerms] {if {[$ip getIoType] == "INPUT" && [[$ip getMTerm] getSigType] != "POWER"} {lappend inputs $ip}}
  if {[llength $inputs] != 1} {break}
  set net [[lindex $inputs 0] getNet]
 }
}
exit
