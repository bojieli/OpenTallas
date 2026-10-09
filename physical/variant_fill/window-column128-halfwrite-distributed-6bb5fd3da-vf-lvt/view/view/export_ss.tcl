read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_L_1x_220121a.lef
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_SS_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_SS_nldm_220122.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_SS_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_SS_nldm_220123.lib
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_SS_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_LVT_SS_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_LVT_SS_nldm_220122.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_LVT_SS_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_LVT_SS_nldm_220123.lib
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_LVT_SS_nldm_211120.lib.gz

read_db /in/results/asap7/opentallas_ot_dsrom_window_column_halfwrite_distributed_asap7_window_column128_halfwrite_distributed_6bb5fd3da_vf_lvt/base/6_final.odb
read_sdc /in/results/asap7/opentallas_ot_dsrom_window_column_halfwrite_distributed_asap7_window_column128_halfwrite_distributed_6bb5fd3da_vf_lvt/base/6_final.sdc
read_spef /in/results/asap7/opentallas_ot_dsrom_window_column_halfwrite_distributed_asap7_window_column128_halfwrite_distributed_6bb5fd3da_vf_lvt/base/6_final.spef
set_propagated_clock [all_clocks]
puts "OT_WS [sta::worst_slack_cmd max]"
write_timing_model -library_name ot_dsrom_window_column_halfwrite_distributed_ss /out/ot_dsrom_window_column_halfwrite_distributed_ss.lib
write_abstract_lef /out/ot_dsrom_window_column_halfwrite_distributed.lef
puts "OT_EXPORT_DONE"
exit
