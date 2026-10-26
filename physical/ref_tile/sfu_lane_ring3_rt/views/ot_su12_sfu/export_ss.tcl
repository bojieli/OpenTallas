read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_SS_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_SS_nldm_220122.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_SS_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_SS_nldm_220123.lib
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_SS_nldm_211120.lib.gz
read_db /in/results/asap7/opentallas_ot_su12_sfu_asap7_ref_sfu_lane_ring3_rt_rt_ae5899467/base/6_final.odb
read_sdc /interface.sdc
read_spef /in/results/asap7/opentallas_ot_su12_sfu_asap7_ref_sfu_lane_ring3_rt_rt_ae5899467/base/6_final.spef
set_propagated_clock [all_clocks]
puts "OT_WS max [sta::worst_slack_cmd max] min [sta::worst_slack_cmd min]"
write_timing_model -library_name ot_su12_sfu_ss /out/ot_su12_sfu_ss.lib
write_abstract_lef /out/ot_su12_sfu.lef
puts "OT_EXPORT_DONE"
exit
