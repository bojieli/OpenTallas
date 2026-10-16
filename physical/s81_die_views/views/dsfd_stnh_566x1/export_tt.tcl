read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_TT_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_TT_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_TT_nldm_211120.lib.gz
read_db /in/results/asap7/opentallas_dsfd_stnh_566x1_asap7_s81g_s81_dsfd_stnh_566x1_2e2d7aa3f_arch/base/6_final.odb
set ::ot_ce_corner tt
read_sdc /in/results/asap7/opentallas_dsfd_stnh_566x1_asap7_s81g_s81_dsfd_stnh_566x1_2e2d7aa3f_arch/base/6_final.sdc
read_spef /in/results/asap7/opentallas_dsfd_stnh_566x1_asap7_s81g_s81_dsfd_stnh_566x1_2e2d7aa3f_arch/base/6_final.spef
set_propagated_clock [all_clocks]
read_sdc /src/physical/s81_die_views/common/signoff_unc60.sdc
read_sdc /src/physical/common_flow/io_ref_routed.sdc
read_sdc /cl/io_ref_routed.sdc
puts "OT_WS max [sta::worst_slack_cmd max] min [sta::worst_slack_cmd min]"
write_timing_model -library_name dsfd_stnh_566x1_tt /out/dsfd_stnh_566x1_tt.lib


puts "OT_EXPORT_DONE"
exit
