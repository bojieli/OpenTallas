read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_lef /mv0/ot_sram_1r1w_64x512_m1_r2c2.lef
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_FF_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_FF_nldm_220122.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_FF_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_FF_nldm_220123.lib
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_FF_nldm_211120.lib.gz
read_liberty /mv0/ot_sram_1r1w_64x512_m1_r2c2_ff.lib
read_db /in/results/asap7/opentallas_dsfd_su_t_qnq_asap7_ref_s81su_qnq_sp8_ref_v5_sp8_2df2353b8/base/6_final.odb
read_sdc /in/results/asap7/opentallas_dsfd_su_t_qnq_asap7_ref_s81su_qnq_sp8_ref_v5_sp8_2df2353b8/base/6_final.sdc
read_spef /in/results/asap7/opentallas_dsfd_su_t_qnq_asap7_ref_s81su_qnq_sp8_ref_v5_sp8_2df2353b8/base/6_final.spef
set_propagated_clock [all_clocks]
read_sdc /src/physical/ref_tile/s81su_qnq_sp8_ref/signoff.sdc
read_sdc /src/physical/common_flow/io_ref_routed.sdc
read_sdc /cl/io_ref_routed.sdc
puts "OT_WS max [sta::worst_slack_cmd max] min [sta::worst_slack_cmd min]"
write_timing_model -library_name dsfd_su_t_qnq_ff /out/dsfd_su_t_qnq_ff.lib


puts "OT_EXPORT_DONE"
exit
