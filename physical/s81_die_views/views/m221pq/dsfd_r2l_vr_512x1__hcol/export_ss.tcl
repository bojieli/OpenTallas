read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_SS_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_SS_nldm_220122.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_SS_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_SS_nldm_220123.lib
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_SS_nldm_211120.lib.gz

read_db /in/results/asap7/opentallas_dsfd_r2l_vr_512x1__hcol_asap7_s81g_s81_hend_m221pq_hcol_pinreg_f1b64667d_tt/base/6_final.odb
read_sdc /in/results/asap7/opentallas_dsfd_r2l_vr_512x1__hcol_asap7_s81g_s81_hend_m221pq_hcol_pinreg_f1b64667d_tt/base/6_final.sdc
read_spef /in/results/asap7/opentallas_dsfd_r2l_vr_512x1__hcol_asap7_s81g_s81_hend_m221pq_hcol_pinreg_f1b64667d_tt/base/6_final.spef
set_propagated_clock [all_clocks]
puts "OT_WS [sta::worst_slack_cmd max]"
write_timing_model -library_name dsfd_r2l_vr_512x1__hcol_ss /out/dsfd_r2l_vr_512x1__hcol_ss.lib
write_abstract_lef /out/dsfd_r2l_vr_512x1__hcol.lef
puts "OT_EXPORT_DONE"
exit
