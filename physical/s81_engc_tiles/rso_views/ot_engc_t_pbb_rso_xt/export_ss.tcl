read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_SS_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_SS_nldm_220122.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_SS_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_SS_nldm_220123.lib
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_SS_nldm_211120.lib.gz
read_liberty /mv0/ot_sram_1r1w_256x256_m2_r2c2_ss.lib
read_lef /mv0/ot_sram_1r1w_256x256_m2_r2c2.lef

read_db /in/results/asap7/opentallas_ot_engc_t_pbb_rso_xt_asap7_qdm_pbbxt25/base/6_final.odb
read_sdc /in/results/asap7/opentallas_ot_engc_t_pbb_rso_xt_asap7_qdm_pbbxt25/base/6_final.sdc
read_spef /in/results/asap7/opentallas_ot_engc_t_pbb_rso_xt_asap7_qdm_pbbxt25/base/6_final.spef
set_propagated_clock [all_clocks]
puts "OT_WS [sta::worst_slack_cmd max]"
write_timing_model -library_name ot_engc_t_pbb_rso_xt_ss /out/ot_engc_t_pbb_rso_xt_ss.lib
write_abstract_lef /out/ot_engc_t_pbb_rso_xt.lef
puts "OT_EXPORT_DONE"
exit
