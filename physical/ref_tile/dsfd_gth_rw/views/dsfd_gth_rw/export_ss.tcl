read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_lef /mv0/ot_sram_1r1w_128x66_m1_r2c2.lef
read_lef /mv1/ot_sram_1r1w_256x34_m2_r2c2.lef
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_SS_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_SS_nldm_220122.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_SS_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_SS_nldm_220123.lib
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_SS_nldm_211120.lib.gz
read_liberty /mv0/ot_sram_1r1w_128x66_m1_r2c2_ss.lib
read_liberty /mv1/ot_sram_1r1w_256x34_m2_r2c2_ss.lib
read_db /work/results/asap7/opentallas_dsfd_gth_rw_asap7_ref_dsfd_gth_rw_pin_repair_1015_pinrepair1_e74771a9c/base/6_final.odb
set ::ot_ce_corner ss
read_sdc /work/results/asap7/opentallas_dsfd_gth_rw_asap7_ref_dsfd_gth_rw_pin_repair_1015_pinrepair1_e74771a9c/base/6_final.sdc
read_spef /work/results/asap7/opentallas_dsfd_gth_rw_asap7_ref_dsfd_gth_rw_pin_repair_1015_pinrepair1_e74771a9c/base/6_final.spef
set_propagated_clock [all_clocks]
read_sdc /src/physical/ref_tile/dsfd_gth_rw_pin_repair_1015/signoff.sdc
read_sdc /src/physical/common_flow/io_ref_routed.sdc
read_sdc /meas/app0_io_ref_routed.sdc
puts "OT_WS max [sta::worst_slack_cmd max] min [sta::worst_slack_cmd min]"
write_timing_model -library_name dsfd_gth_rw_ss /out/dsfd_gth_rw_ss.lib
write_abstract_lef /out/dsfd_gth_rw.lef

puts "OT_EXPORT_DONE"
exit
