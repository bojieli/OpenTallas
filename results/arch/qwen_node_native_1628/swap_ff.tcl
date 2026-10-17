read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_FF_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_FF_nldm_220122.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_FF_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_FF_nldm_220123.lib
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_FF_nldm_211120.lib.gz
read_db /work/results/asap7/opentallas_ot_qwen_tile_node_asap7_ref_ot_qwen_tile_node_r5_78b36aae5/base/6_final.odb
read_sdc /work/results/asap7/opentallas_ot_qwen_tile_node_asap7_ref_ot_qwen_tile_node_r5_78b36aae5/base/6_final.sdc
read_spef /work/results/asap7/opentallas_ot_qwen_tile_node_asap7_ref_ot_qwen_tile_node_r5_78b36aae5/base/6_final.spef
set_propagated_clock [all_clocks]
read_sdc /work/w18_extra.sdc
read_sdc /meas/app0_io_ref_routed.sdc
set block [ord::get_db_block]
set n 0
foreach inst [$block getInsts] {
 if {[string match "ot_outhold_*" [$inst getName]] && [[$inst getMaster] getName] eq "HB4xp67_ASAP7_75t_R"} {
   set m [$inst getMaster]; set lib [$m getLib]; set repl [$lib findMaster HB2xp67_ASAP7_75t_R]
   if {$repl eq "NULL"} {error "missing HB2"}
   $inst setDoNotTouch false
   $inst swapMaster $repl
   incr n
 }
}
puts "NODE_SWAP $n output HB4 to HB2, unchanged placement/wires/SPEF (diagnostic only)"
puts "OT_WS max [sta::worst_slack_cmd max] min [sta::worst_slack_cmd min]"
report_checks -to [all_outputs] -path_delay max -group_path_count 4 -fields {slew cap fanout input nets} -format full_clock_expanded
report_checks -to [all_outputs] -path_delay min -group_path_count 4 -fields {slew cap fanout input nets} -format full_clock_expanded
exit
