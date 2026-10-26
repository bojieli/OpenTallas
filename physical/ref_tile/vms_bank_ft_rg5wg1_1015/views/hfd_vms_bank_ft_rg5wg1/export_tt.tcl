read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_L_1x_220121a.lef
read_lef /mv0/ot_sram_1r1w_1024x256_m2_r2c2.lef
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_TT_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_TT_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_TT_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_LVT_TT_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_LVT_TT_nldm_220122.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_LVT_TT_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_LVT_TT_nldm_220123.lib
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_LVT_TT_nldm_211120.lib.gz
read_liberty /mv0/ot_sram_1r1w_1024x256_m2_r2c2_tt.lib
read_db /work/results/asap7/opentallas_hfd_vms_bank_ft_rg5wg1_asap7_ref_vms_bank_ft_rg5wg1_1015_sp2_a3813e240/base/6_final.odb
set ::ot_ce_corner tt
read_sdc /work/results/asap7/opentallas_hfd_vms_bank_ft_rg5wg1_asap7_ref_vms_bank_ft_rg5wg1_1015_sp2_a3813e240/base/6_final.sdc
read_spef /work/results/asap7/opentallas_hfd_vms_bank_ft_rg5wg1_asap7_ref_vms_bank_ft_rg5wg1_1015_sp2_a3813e240/base/6_final.spef
set_propagated_clock [all_clocks]
read_sdc /src/physical/ref_tile/vms_bank_ft_rg5wg1_1015/signoff.sdc
read_sdc /src/physical/common_flow/io_ref_routed.sdc
read_sdc /meas/app0_io_ref_routed.sdc
puts "OT_WS max [sta::worst_slack_cmd max] min [sta::worst_slack_cmd min]"
write_timing_model -library_name hfd_vms_bank_ft_rg5wg1_tt /out/hfd_vms_bank_ft_rg5wg1_tt.lib


puts "OT_EXPORT_DONE"
exit
