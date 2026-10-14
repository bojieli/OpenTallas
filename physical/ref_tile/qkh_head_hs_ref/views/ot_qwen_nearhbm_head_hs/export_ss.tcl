read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_lef /mv0/ot_qkh_ktree.lef
read_lef /mv1/ot_qkh_lane8.lef
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_SS_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_SS_nldm_220122.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_SS_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_SS_nldm_220123.lib
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_SS_nldm_211120.lib.gz
read_liberty /mv0/ot_qkh_ktree_ss.lib
read_liberty /mv1/ot_qkh_lane8_ss.lib
read_db /work/results/asap7/opentallas_ot_qwen_nearhbm_head_hs_asap7_ref_qkh_head_hs_ref_q13b_54a543b22/base/6_final.odb
read_sdc /work/results/asap7/opentallas_ot_qwen_nearhbm_head_hs_asap7_ref_qkh_head_hs_ref_q13b_54a543b22/base/6_final.sdc
read_spef /work/results/asap7/opentallas_ot_qwen_nearhbm_head_hs_asap7_ref_qkh_head_hs_ref_q13b_54a543b22/base/6_final.spef
set_propagated_clock [all_clocks]
read_sdc /src/physical/ref_tile/qkh_head_hs_ref/signoff.sdc
read_sdc /src/physical/common_flow/io_ref_routed.sdc
read_sdc /meas/app0_io_ref_routed.sdc
puts "OT_WS max [sta::worst_slack_cmd max] min [sta::worst_slack_cmd min]"
write_timing_model -library_name ot_qwen_nearhbm_head_hs_ss /out/ot_qwen_nearhbm_head_hs_ss.lib
write_abstract_lef /out/ot_qwen_nearhbm_head_hs.lef

puts "OT_EXPORT_DONE"
exit
