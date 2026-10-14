read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_lef /mv0/ot_hdc_vstream_lane_h.lef
read_lef /mv1/ot_hdc_sfu_exp_t.lef
read_lef /mv2/ot_hdc_sfu_rcp_t.lef
read_lef /mv3/ot_hdc_sfu_rsq_t.lef
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_FF_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_FF_nldm_220122.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_FF_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_FF_nldm_220123.lib
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_FF_nldm_211120.lib.gz
read_liberty /mv0/ot_hdc_vstream_lane_h_ff.lib
read_liberty /mv1/ot_hdc_sfu_exp_t_ff.lib
read_liberty /mv2/ot_hdc_sfu_rcp_t_ff.lib
read_liberty /mv3/ot_hdc_sfu_rsq_t_ff.lib
read_db /work/results/asap7/opentallas_ot_hdc_vstream_lane_t_asap7_ref_qfd_su_lane_t_io_io1_60bc0119d/base/6_final.odb
set ::ot_ce_corner ff
read_sdc /work/results/asap7/opentallas_ot_hdc_vstream_lane_t_asap7_ref_qfd_su_lane_t_io_io1_60bc0119d/base/6_final.sdc
read_spef /work/results/asap7/opentallas_ot_hdc_vstream_lane_t_asap7_ref_qfd_su_lane_t_io_io1_60bc0119d/base/6_final.spef
set_propagated_clock [all_clocks]
read_sdc /src/physical/ref_tile/qfd_su_lane_t_io/signoff.sdc
read_sdc /src/physical/common_flow/io_ref_routed.sdc
read_sdc /meas/app0_io_ref_routed.sdc
puts "OT_WS max [sta::worst_slack_cmd max] min [sta::worst_slack_cmd min]"
write_timing_model -library_name ot_hdc_vstream_lane_t_ff /out/ot_hdc_vstream_lane_t_ff.lib


puts "OT_EXPORT_DONE"
exit
