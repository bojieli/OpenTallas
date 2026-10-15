read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_lef /mv0/ot_sram_1r1w_256x256_m2_r2c2.lef
read_lef /mv1/qvm_data256_native.lef
read_lef /mv2/qvm_bank_ctrl_native.lef
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_FF_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_FF_nldm_220122.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_FF_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_FF_nldm_220123.lib
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_FF_nldm_211120.lib.gz
read_liberty /mv0/ot_sram_1r1w_256x256_m2_r2c2_ff.lib
read_liberty /mv1/qvm_data256_native_ff.lib
read_liberty /mv2/qvm_bank_ctrl_native_ff.lib
read_db /work/results/asap7/opentallas_qvm_bank_banked_native_asap7_ref_qvm_bank_entries_my_native_ne2_8e2cd3d55/base/6_final.odb
set ::ot_ce_corner ff
read_sdc /work/results/asap7/opentallas_qvm_bank_banked_native_asap7_ref_qvm_bank_entries_my_native_ne2_8e2cd3d55/base/6_final.sdc
read_spef /work/results/asap7/opentallas_qvm_bank_banked_native_asap7_ref_qvm_bank_entries_my_native_ne2_8e2cd3d55/base/6_final.spef
set_propagated_clock [all_clocks]
read_sdc /work/w18_extra.sdc
read_sdc /meas/app0_io_ref_routed.sdc
puts "OT_WS max [sta::worst_slack_cmd max] min [sta::worst_slack_cmd min]"
write_timing_model -library_name qvm_bank_banked_native_ff /out/qvm_bank_banked_native_ff.lib


puts "OT_EXPORT_DONE"
exit
