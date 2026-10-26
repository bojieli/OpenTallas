read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_TT_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_TT_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_TT_nldm_211120.lib.gz
read_db /work/results/asap7/opentallas_ot_smh_tr_w128_s2_m0_asap7_ref_smh_tr_w128_s2_m0_ref_split1_e22843bcd/base/6_final.odb
set ::ot_ce_corner ss
read_sdc /work/results/asap7/opentallas_ot_smh_tr_w128_s2_m0_asap7_ref_smh_tr_w128_s2_m0_ref_split1_e22843bcd/base/6_final.sdc
read_spef /work/results/asap7/opentallas_ot_smh_tr_w128_s2_m0_asap7_ref_smh_tr_w128_s2_m0_ref_split1_e22843bcd/base/6_final.spef
set_propagated_clock [all_clocks]
read_sdc /work/w18_extra.sdc
read_sdc /meas/app0_io_ref_routed.sdc
puts "OT_WS max [sta::worst_slack_cmd max] min [sta::worst_slack_cmd min]"
write_timing_model -library_name ot_smh_tr_w128_s2_m0_tt /out/ot_smh_tr_w128_s2_m0_tt.lib


puts "OT_EXPORT_DONE"
exit
