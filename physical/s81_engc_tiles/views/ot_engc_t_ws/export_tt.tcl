read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_TT_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_TT_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_TT_nldm_211120.lib.gz
read_db /work/results/asap7/opentallas_ot_engc_t_ws_asap7_qdm_el1011_engc_ws_pke_a804fc09b_tc_cl/base/6_final.odb
read_sdc /work/results/asap7/opentallas_ot_engc_t_ws_asap7_qdm_el1011_engc_ws_pke_a804fc09b_tc_cl/base/6_final.sdc
read_spef /work/results/asap7/opentallas_ot_engc_t_ws_asap7_qdm_el1011_engc_ws_pke_a804fc09b_tc_cl/base/6_final.spef
set_propagated_clock [all_clocks]
read_sdc /src/physical/qwen_die_masters/signoff/engc_ws_a.sdc
read_sdc /src/physical/common_flow/io_ref_routed.sdc
read_sdc /meas/app0_io_ref_routed.sdc
puts "OT_WS max [sta::worst_slack_cmd max] min [sta::worst_slack_cmd min]"
write_timing_model -library_name ot_engc_t_ws_tt /out/ot_engc_t_ws_tt.lib


puts "OT_EXPORT_DONE"
exit
