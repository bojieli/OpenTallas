read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_lef /mv0/dsfd_coll_cescn.lef
read_lef /mv1/dsfd_coll_cesl.lef
read_lef /mv2/dsfd_coll_ceso.lef
read_lef /mv3/dsfd_coll_cespn.lef
read_lef /mv4/dsfd_coll_cesx.lef
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_FF_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_FF_nldm_220122.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_FF_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_FF_nldm_220123.lib
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_FF_nldm_211120.lib.gz
read_liberty /mv0/dsfd_coll_cescn_ff.lib
read_liberty /mv1/dsfd_coll_cesl_ff.lib
read_liberty /mv2/dsfd_coll_ceso_ff.lib
read_liberty /mv3/dsfd_coll_cespn_ff.lib
read_liberty /mv4/dsfd_coll_cesx_ff.lib
read_db /work/results/asap7/opentallas_dsfd_coll_cesn_asap7_ref_dscoll_cesn_sp_sp1_d4bed2783/base/6_final.odb
read_sdc /work/results/asap7/opentallas_dsfd_coll_cesn_asap7_ref_dscoll_cesn_sp_sp1_d4bed2783/base/6_final.sdc
read_spef /work/results/asap7/opentallas_dsfd_coll_cesn_asap7_ref_dscoll_cesn_sp_sp1_d4bed2783/base/6_final.spef
set_propagated_clock [all_clocks]
read_sdc /work/w18_extra.sdc
read_sdc /meas/app0_io_ref_routed.sdc
puts "OT_WS max [sta::worst_slack_cmd max] min [sta::worst_slack_cmd min]"
write_timing_model -library_name dsfd_coll_cesn_ff /out/dsfd_coll_cesn_ff.lib


puts "OT_EXPORT_DONE"
exit
