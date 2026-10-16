read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_FF_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_FF_nldm_220122.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_FF_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_FF_nldm_220123.lib
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_FF_nldm_211120.lib.gz

read_db /in/results/asap7/opentallas_ot_dsrom_mtp_lrx_rtt_asap7_mtp_rtt512_f9r10_d23p1_09dc8fad4_hm10/base/6_final.odb
read_sdc /in/results/asap7/opentallas_ot_dsrom_mtp_lrx_rtt_asap7_mtp_rtt512_f9r10_d23p1_09dc8fad4_hm10/base/6_final.sdc
read_spef /in/results/asap7/opentallas_ot_dsrom_mtp_lrx_rtt_asap7_mtp_rtt512_f9r10_d23p1_09dc8fad4_hm10/base/6_final.spef
set_propagated_clock [all_clocks]
puts "OT_WS [sta::worst_slack_cmd min]"
write_timing_model -library_name ot_dsrom_mtp_lrx_rtt_ff /out/ot_dsrom_mtp_lrx_rtt_ff.lib
puts "OT_EXPORT_DONE"
exit
