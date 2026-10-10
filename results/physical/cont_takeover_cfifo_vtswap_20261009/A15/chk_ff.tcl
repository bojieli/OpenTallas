read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_FF_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_FF_nldm_220122.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_FF_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_FF_nldm_220123.lib
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_FF_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_LVT_FF_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_LVT_FF_nldm_220122.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_LVT_FF_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_LVT_FF_nldm_220123.lib
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_LVT_FF_nldm_211120.lib.gz
read_db /out/6_final_vtswap.odb
read_sdc /work/results/asap7/opentallas_dsfd_cfifo_asap7_s81g_s81_dsfd_cfifo_colck_a6ca75fbe_tt_srcfix/base/6_final.sdc
read_spef /work/results/asap7/opentallas_dsfd_cfifo_asap7_s81g_s81_dsfd_cfifo_colck_a6ca75fbe_tt_srcfix/base/6_final.spef
set_propagated_clock [all_clocks]
read_sdc /src/physical/s81_die_views/common/signoff_unc60.sdc
read_sdc /meas/app0_io_ref_routed.sdc
puts "OT_CORNER ff"

puts "OT_FF_HOLD [sta::worst_slack_cmd min]"
report_checks -path_delay min -group_path_count 1 -format full_clock_expanded
set n 0; foreach i [[ord::get_db_block] getInsts] { if {[string match *_ASAP7_75t_L [[$i getMaster] getName]]} { incr n } }
puts "OT_FF_LVT_COUNT $n"
exit
