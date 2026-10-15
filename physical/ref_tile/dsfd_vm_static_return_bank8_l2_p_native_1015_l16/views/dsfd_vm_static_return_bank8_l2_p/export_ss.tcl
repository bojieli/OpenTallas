read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_SS_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_SS_nldm_220122.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_SS_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_SS_nldm_220123.lib
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_SS_nldm_211120.lib.gz
read_db /work/results/asap7/opentallas_dsfd_vm_static_return_bank8_l2_p_asap7_ref_dsfd_vm_static_return_bank8_l2_p_native_1015_l16_l16_ceea362ab_arg2/base/6_final.odb
set ::ot_ce_corner ss
read_sdc /work/results/asap7/opentallas_dsfd_vm_static_return_bank8_l2_p_asap7_ref_dsfd_vm_static_return_bank8_l2_p_native_1015_l16_l16_ceea362ab_arg2/base/6_final.sdc
read_spef /work/results/asap7/opentallas_dsfd_vm_static_return_bank8_l2_p_asap7_ref_dsfd_vm_static_return_bank8_l2_p_native_1015_l16_l16_ceea362ab_arg2/base/6_final.spef
set_propagated_clock [all_clocks]
read_sdc /work/w18_extra.sdc
read_sdc /meas/app0_io_ref_routed.sdc
puts "OT_WS max [sta::worst_slack_cmd max] min [sta::worst_slack_cmd min]"
write_timing_model -library_name dsfd_vm_static_return_bank8_l2_p_ss /out/dsfd_vm_static_return_bank8_l2_p_ss.lib
write_abstract_lef /out/dsfd_vm_static_return_bank8_l2_p.lef

puts "OT_EXPORT_DONE"
exit
