read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_lef /mv0/ot_sram_1r1w_1024x256_m2_r2c2.lef
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_SS_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_SS_nldm_220122.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_SS_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_SS_nldm_220123.lib
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_SS_nldm_211120.lib.gz
read_liberty /mv0/ot_sram_1r1w_1024x256_m2_r2c2_ss.lib
read_db /in/results/asap7/opentallas_ot_hgi_qdq_sw_program_leaf_asap7_ref_gate/base/6_final.odb
read_sdc /in/results/asap7/opentallas_ot_hgi_qdq_sw_program_leaf_asap7_ref_gate/base/6_final.sdc
read_spef /in/results/asap7/opentallas_ot_hgi_qdq_sw_program_leaf_asap7_ref_gate/base/6_final.spef
set_propagated_clock [all_clocks]
read_sdc /post0.sdc
read_sdc /post1.sdc
puts "OT_WS max [sta::worst_slack_cmd max] min [sta::worst_slack_cmd min]"
write_timing_model -library_name ot_hgi_qdq_sw_program_leaf_ss /out/ot_hgi_qdq_sw_program_leaf_ss.lib
write_abstract_lef /out/ot_hgi_qdq_sw_program_leaf.lef

puts "OT_EXPORT_DONE"
exit
