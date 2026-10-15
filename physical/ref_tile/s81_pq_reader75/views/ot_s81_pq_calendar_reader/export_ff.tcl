read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_FF_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_FF_nldm_220122.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_FF_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_FF_nldm_220123.lib
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_FF_nldm_211120.lib.gz
read_db /work/results/asap7/opentallas_ot_s81_pq_calendar_reader_asap7_ref_s81_pq_reader75_rstrelay_r3_182180c59/base/6_final.odb
set ::ot_ce_corner ff
read_sdc /work/results/asap7/opentallas_ot_s81_pq_calendar_reader_asap7_ref_s81_pq_reader75_rstrelay_r3_182180c59/base/6_final.sdc
read_spef /work/results/asap7/opentallas_ot_s81_pq_calendar_reader_asap7_ref_s81_pq_reader75_rstrelay_r3_182180c59/base/6_final.spef
set_propagated_clock [all_clocks]
read_sdc /work/w18_extra.sdc
read_sdc /meas/app0_io_ref_routed.sdc
puts "OT_WS max [sta::worst_slack_cmd max] min [sta::worst_slack_cmd min]"
write_timing_model -library_name ot_s81_pq_calendar_reader_ff /out/ot_s81_pq_calendar_reader_ff.lib


puts "OT_EXPORT_DONE"
exit
