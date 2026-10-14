read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_lef /mv0/ot_rom_4096x274_m8.lef
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_SS_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_SS_nldm_220122.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_SS_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_SS_nldm_220123.lib
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_SS_nldm_211120.lib.gz
read_liberty /mv0/ot_rom_4096x274_m8_ss.lib
read_db /work/results/asap7/opentallas_ot_v41_bf_col_asap7_bfh_compact199_col_kreg_a1200_05a8d46ee_cl/base/6_final.odb
read_sdc /work/results/asap7/opentallas_ot_v41_bf_col_asap7_bfh_compact199_col_kreg_a1200_05a8d46ee_cl/base/6_final.sdc
read_spef /work/results/asap7/opentallas_ot_v41_bf_col_asap7_bfh_compact199_col_kreg_a1200_05a8d46ee_cl/base/6_final.spef
set_propagated_clock [all_clocks]
read_sdc /src/physical/s81_bf_hier/signoff_col.sdc
read_sdc /src/physical/common_flow/io_ref_routed.sdc
read_sdc /meas/app0_io_ref_routed.sdc
puts "OT_WS max [sta::worst_slack_cmd max] min [sta::worst_slack_cmd min]"
write_timing_model -library_name ot_v41_bf_col_ss /out/ot_v41_bf_col_ss.lib
write_abstract_lef /out/ot_v41_bf_col.lef

puts "OT_EXPORT_DONE"
exit
