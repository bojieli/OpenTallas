read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_FF_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_FF_nldm_220122.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_FF_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_FF_nldm_220123.lib
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_FF_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_DFFHQNH2V2X_RVT_FF_nldm_FAKE.lib
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_DFFHQNV2X_RVT_FF_nldm_FAKE.lib
read_db /work/results/asap7/chip_ot_gpu_tc_col/base/6_final.odb
read_sdc /work/results/asap7/chip_ot_gpu_tc_col/base/6_final.sdc
read_spef /work/results/asap7/chip_ot_gpu_tc_col/base/6_final.spef
set_propagated_clock [all_clocks]
set_clock_uncertainty 0 [all_clocks]
set_clock_uncertainty -hold 25 [all_clocks]
puts "OTC setup_wns [sta::worst_slack_cmd max]"
puts "OTC hold_wns [sta::worst_slack_cmd min]"
puts "OTC setup_tns [sta::total_negative_slack_cmd max]"
puts "OTC hold_tns [sta::total_negative_slack_cmd min]"
report_checks -path_delay max -digits 1 -fields {slew cap} > /work/corner_ff_max.rpt
report_checks -path_delay min -digits 1 > /work/corner_ff_min.rpt
set n 0; set a 0.0
foreach i [[ord::get_db_block] getInsts] { if {[string match hold* [$i getName]]} { incr n; set m [$i getMaster]; set a [expr {$a + [$m getWidth] * [$m getHeight]}] } }
puts "OTC hold_buffers $n"
puts "OTC hold_buffer_dbu2 $a"
puts "OTC dbu [[ord::get_db_tech] getDbUnitsPerMicron]"
write_timing_model -library_name ot_gpu_tc_col_ff /work/ot_gpu_tc_col_ff.lib
