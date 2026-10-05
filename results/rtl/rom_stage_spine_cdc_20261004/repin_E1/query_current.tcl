set_thread_count 1
define_corners WC BC
read_liberty -corner WC /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_SS_nldm_211120.lib.gz
read_liberty -corner WC /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_SS_nldm_220122.lib.gz
read_liberty -corner WC /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_SS_nldm_211120.lib.gz
read_liberty -corner WC /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_SS_nldm_220123.lib
read_liberty -corner WC /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_SS_nldm_211120.lib.gz
read_liberty -corner WC /src/physical/asap7_memory_macros/ot_rom_4096x274_m8/ot_rom_4096x274_m8_ss.lib
read_liberty -corner BC /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_FF_nldm_211120.lib.gz
read_liberty -corner BC /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_FF_nldm_220122.lib.gz
read_liberty -corner BC /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_FF_nldm_211120.lib.gz
read_liberty -corner BC /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_FF_nldm_220123.lib
read_liberty -corner BC /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_FF_nldm_211120.lib.gz
read_liberty -corner BC /src/physical/asap7_memory_macros/ot_rom_4096x274_m8/ot_rom_4096x274_m8_ff.lib
read_db /work/results/asap7/opentallas_ot_v41_rom_stage_q_pg_cdc_w10_asap7_spine_cdc_E1_current_cts1_20261004/base/4_cts.odb
read_sdc /work/results/asap7/opentallas_ot_v41_rom_stage_q_pg_cdc_w10_asap7_spine_cdc_E1_current_cts1_20261004/base/4_cts.sdc
source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl
estimate_parasitics -placement
set_cmd_units -time ps
set dbu [[ord::get_db_tech] getDbUnitsPerMicron]
foreach bt [[ord::get_db_block] getBTerms] { if {[$bt getSigType] eq "SIGNAL" || [$bt getSigType] eq "CLOCK"} { foreach bp [$bt getBPins] { foreach b [$bp getBoxes] { puts "PIN [$bt getName] [[$b getTechLayer] getName] [$b xMin] [$b yMin] [$b xMax] [$b yMax] DBU=$dbu" } } } }
foreach i [[ord::get_db_block] getInsts] { if {[[$i getMaster] isBlock]} {set b [$i getBBox]; puts "MACRO [$i getName] [$i getOrient] [$b xMin] [$b yMin] [$b xMax] [$b yMax] DBU=$dbu"} }
puts "GROUP xs_q0 max WC"
report_checks -from [get_ports {xs_q0[*]}] -path_delay max -corner WC -group_count 1 -endpoint_count 1 -format full_clock_expanded
puts "GROUP xs_q0 min BC"
report_checks -from [get_ports {xs_q0[*]}] -path_delay min -corner BC -group_count 1 -endpoint_count 1 -format full_clock_expanded
puts "GROUP xs_q1 max WC"
report_checks -from [get_ports {xs_q1[*]}] -path_delay max -corner WC -group_count 1 -endpoint_count 1 -format full_clock_expanded
puts "GROUP xs_q1 min BC"
report_checks -from [get_ports {xs_q1[*]}] -path_delay min -corner BC -group_count 1 -endpoint_count 1 -format full_clock_expanded
puts "GROUP xs_e0 max WC"
report_checks -from [get_ports {xs_e0[*]}] -path_delay max -corner WC -group_count 1 -endpoint_count 1 -format full_clock_expanded
puts "GROUP xs_e0 min BC"
report_checks -from [get_ports {xs_e0[*]}] -path_delay min -corner BC -group_count 1 -endpoint_count 1 -format full_clock_expanded
puts "GROUP xs_e1 max WC"
report_checks -from [get_ports {xs_e1[*]}] -path_delay max -corner WC -group_count 1 -endpoint_count 1 -format full_clock_expanded
puts "GROUP xs_e1 min BC"
report_checks -from [get_ports {xs_e1[*]}] -path_delay min -corner BC -group_count 1 -endpoint_count 1 -format full_clock_expanded
puts "GROUP pval max WC"
report_checks -to [get_ports {pval[*]}] -path_delay max -corner WC -group_count 1 -endpoint_count 1 -format full_clock_expanded
puts "GROUP pval min BC"
report_checks -to [get_ports {pval[*]}] -path_delay min -corner BC -group_count 1 -endpoint_count 1 -format full_clock_expanded
puts "GROUP prow max WC"
report_checks -to [get_ports {prow[*]}] -path_delay max -corner WC -group_count 1 -endpoint_count 1 -format full_clock_expanded
puts "GROUP prow min BC"
report_checks -to [get_ports {prow[*]}] -path_delay min -corner BC -group_count 1 -endpoint_count 1 -format full_clock_expanded
puts "GROUP pseg max WC"
report_checks -to [get_ports {pseg[*]}] -path_delay max -corner WC -group_count 1 -endpoint_count 1 -format full_clock_expanded
puts "GROUP pseg min BC"
report_checks -to [get_ports {pseg[*]}] -path_delay min -corner BC -group_count 1 -endpoint_count 1 -format full_clock_expanded
puts "GROUP pnseg max WC"
report_checks -to [get_ports {pnseg[*]}] -path_delay max -corner WC -group_count 1 -endpoint_count 1 -format full_clock_expanded
puts "GROUP pnseg min BC"
report_checks -to [get_ports {pnseg[*]}] -path_delay min -corner BC -group_count 1 -endpoint_count 1 -format full_clock_expanded
puts "GROUP ppos max WC"
report_checks -to [get_ports {ppos[*]}] -path_delay max -corner WC -group_count 1 -endpoint_count 1 -format full_clock_expanded
puts "GROUP ppos min BC"
report_checks -to [get_ports {ppos[*]}] -path_delay min -corner BC -group_count 1 -endpoint_count 1 -format full_clock_expanded
puts "GROUP pv max WC"
report_checks -to [get_ports {pv[*]}] -path_delay max -corner WC -group_count 1 -endpoint_count 1 -format full_clock_expanded
puts "GROUP pv min BC"
report_checks -to [get_ports {pv[*]}] -path_delay min -corner BC -group_count 1 -endpoint_count 1 -format full_clock_expanded
puts "GROUP perr max WC"
report_checks -to [get_ports {perr[*]}] -path_delay max -corner WC -group_count 1 -endpoint_count 1 -format full_clock_expanded
puts "GROUP perr min BC"
report_checks -to [get_ports {perr[*]}] -path_delay min -corner BC -group_count 1 -endpoint_count 1 -format full_clock_expanded
puts "GROUP busy max WC"
report_checks -to [get_ports {busy[*]}] -path_delay max -corner WC -group_count 1 -endpoint_count 1 -format full_clock_expanded
puts "GROUP busy min BC"
report_checks -to [get_ports {busy[*]}] -path_delay min -corner BC -group_count 1 -endpoint_count 1 -format full_clock_expanded
puts "GROUP fault max WC"
report_checks -to [get_ports {fault[*]}] -path_delay max -corner WC -group_count 1 -endpoint_count 1 -format full_clock_expanded
puts "GROUP fault min BC"
report_checks -to [get_ports {fault[*]}] -path_delay min -corner BC -group_count 1 -endpoint_count 1 -format full_clock_expanded
