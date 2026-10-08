read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_FF_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_FF_nldm_220122.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_FF_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_FF_nldm_220123.lib
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_FF_nldm_211120.lib.gz

read_db /in/results/asap7/opentallas_dsfd_capt_grp_asap7_s81ph_s81ph_dsfd_capt_grp_1c8d4c45f_tt/base/6_final.odb
read_sdc /in/results/asap7/opentallas_dsfd_capt_grp_asap7_s81ph_s81ph_dsfd_capt_grp_1c8d4c45f_tt/base/6_final.sdc
read_spef /in/results/asap7/opentallas_dsfd_capt_grp_asap7_s81ph_s81ph_dsfd_capt_grp_1c8d4c45f_tt/base/6_final.spef
set_propagated_clock [all_clocks]
puts "OT_WS [sta::worst_slack_cmd min]"
write_timing_model -library_name dsfd_capt_grp_ff /out/dsfd_capt_grp_ff.lib
puts "OT_EXPORT_DONE"
exit
