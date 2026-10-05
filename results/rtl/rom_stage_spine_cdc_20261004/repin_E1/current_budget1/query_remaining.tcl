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

puts "GROUP xs_v max WC"
report_checks -from [get_ports {xs_v*}] -path_delay max -corner WC -group_count 1 -endpoint_count 1 -format full_clock_expanded
puts "GROUP xs_v min BC"
report_checks -from [get_ports {xs_v*}] -path_delay min -corner BC -group_count 1 -endpoint_count 1 -format full_clock_expanded
puts "GROUP xs_p max WC"
report_checks -from [get_ports {xs_p*}] -path_delay max -corner WC -group_count 1 -endpoint_count 1 -format full_clock_expanded
puts "GROUP xs_p min BC"
report_checks -from [get_ports {xs_p*}] -path_delay min -corner BC -group_count 1 -endpoint_count 1 -format full_clock_expanded
puts "GROUP xs_b max WC"
report_checks -from [get_ports {xs_b*}] -path_delay max -corner WC -group_count 1 -endpoint_count 1 -format full_clock_expanded
puts "GROUP xs_b min BC"
report_checks -from [get_ports {xs_b*}] -path_delay min -corner BC -group_count 1 -endpoint_count 1 -format full_clock_expanded
puts "GROUP xs_sv max WC"
report_checks -from [get_ports {xs_sv*}] -path_delay max -corner WC -group_count 1 -endpoint_count 1 -format full_clock_expanded
puts "GROUP xs_sv min BC"
report_checks -from [get_ports {xs_sv*}] -path_delay min -corner BC -group_count 1 -endpoint_count 1 -format full_clock_expanded
puts "GROUP xs_pos max WC"
report_checks -from [get_ports {xs_pos*}] -path_delay max -corner WC -group_count 1 -endpoint_count 1 -format full_clock_expanded
puts "GROUP xs_pos min BC"
report_checks -from [get_ports {xs_pos*}] -path_delay min -corner BC -group_count 1 -endpoint_count 1 -format full_clock_expanded
puts "GROUP cfg_v max WC"
report_checks -from [get_ports {cfg_v*}] -path_delay max -corner WC -group_count 1 -endpoint_count 1 -format full_clock_expanded
puts "GROUP cfg_v min BC"
report_checks -from [get_ports {cfg_v*}] -path_delay min -corner BC -group_count 1 -endpoint_count 1 -format full_clock_expanded
puts "GROUP cfg_a max WC"
report_checks -from [get_ports {cfg_a*}] -path_delay max -corner WC -group_count 1 -endpoint_count 1 -format full_clock_expanded
puts "GROUP cfg_a min BC"
report_checks -from [get_ports {cfg_a*}] -path_delay min -corner BC -group_count 1 -endpoint_count 1 -format full_clock_expanded
puts "GROUP cfg_d max WC"
report_checks -from [get_ports {cfg_d*}] -path_delay max -corner WC -group_count 1 -endpoint_count 1 -format full_clock_expanded
puts "GROUP cfg_d min BC"
report_checks -from [get_ports {cfg_d*}] -path_delay min -corner BC -group_count 1 -endpoint_count 1 -format full_clock_expanded
puts "GROUP go max WC"
report_checks -from [get_ports {go*}] -path_delay max -corner WC -group_count 1 -endpoint_count 1 -format full_clock_expanded
puts "GROUP go min BC"
report_checks -from [get_ports {go*}] -path_delay min -corner BC -group_count 1 -endpoint_count 1 -format full_clock_expanded
puts "GROUP rst_n max WC"
report_checks -from [get_ports {rst_n*}] -path_delay max -corner WC -group_count 1 -endpoint_count 1 -format full_clock_expanded
puts "GROUP rst_n min BC"
report_checks -from [get_ports {rst_n*}] -path_delay min -corner BC -group_count 1 -endpoint_count 1 -format full_clock_expanded
puts "GROUP pg_en max WC"
report_checks -from [get_ports {pg_en*}] -path_delay max -corner WC -group_count 1 -endpoint_count 1 -format full_clock_expanded
puts "GROUP pg_en min BC"
report_checks -from [get_ports {pg_en*}] -path_delay min -corner BC -group_count 1 -endpoint_count 1 -format full_clock_expanded
puts "GROUP sched_v max WC"
report_checks -from [get_ports {sched_v*}] -path_delay max -corner WC -group_count 1 -endpoint_count 1 -format full_clock_expanded
puts "GROUP sched_v min BC"
report_checks -from [get_ports {sched_v*}] -path_delay min -corner BC -group_count 1 -endpoint_count 1 -format full_clock_expanded
puts "GROUP sched_gap max WC"
report_checks -from [get_ports {sched_gap*}] -path_delay max -corner WC -group_count 1 -endpoint_count 1 -format full_clock_expanded
puts "GROUP sched_gap min BC"
report_checks -from [get_ports {sched_gap*}] -path_delay min -corner BC -group_count 1 -endpoint_count 1 -format full_clock_expanded
puts "GROUP pg_lead max WC"
report_checks -from [get_ports {pg_lead*}] -path_delay max -corner WC -group_count 1 -endpoint_count 1 -format full_clock_expanded
puts "GROUP pg_lead min BC"
report_checks -from [get_ports {pg_lead*}] -path_delay min -corner BC -group_count 1 -endpoint_count 1 -format full_clock_expanded
puts "GROUP pg_bet max WC"
report_checks -from [get_ports {pg_bet*}] -path_delay max -corner WC -group_count 1 -endpoint_count 1 -format full_clock_expanded
puts "GROUP pg_bet min BC"
report_checks -from [get_ports {pg_bet*}] -path_delay min -corner BC -group_count 1 -endpoint_count 1 -format full_clock_expanded
puts "GROUP pg_idle max WC"
report_checks -from [get_ports {pg_idle*}] -path_delay max -corner WC -group_count 1 -endpoint_count 1 -format full_clock_expanded
puts "GROUP pg_idle min BC"
report_checks -from [get_ports {pg_idle*}] -path_delay min -corner BC -group_count 1 -endpoint_count 1 -format full_clock_expanded
puts "GROUP pg_step max WC"
report_checks -from [get_ports {pg_step*}] -path_delay max -corner WC -group_count 1 -endpoint_count 1 -format full_clock_expanded
puts "GROUP pg_step min BC"
report_checks -from [get_ports {pg_step*}] -path_delay min -corner BC -group_count 1 -endpoint_count 1 -format full_clock_expanded
puts "GROUP pg_rst max WC"
report_checks -from [get_ports {pg_rst*}] -path_delay max -corner WC -group_count 1 -endpoint_count 1 -format full_clock_expanded
puts "GROUP pg_rst min BC"
report_checks -from [get_ports {pg_rst*}] -path_delay min -corner BC -group_count 1 -endpoint_count 1 -format full_clock_expanded
puts "GROUP pg_ack_to max WC"
report_checks -from [get_ports {pg_ack_to*}] -path_delay max -corner WC -group_count 1 -endpoint_count 1 -format full_clock_expanded
puts "GROUP pg_ack_to min BC"
report_checks -from [get_ports {pg_ack_to*}] -path_delay min -corner BC -group_count 1 -endpoint_count 1 -format full_clock_expanded
puts "GROUP sw_ack max WC"
report_checks -from [get_ports {sw_ack*}] -path_delay max -corner WC -group_count 1 -endpoint_count 1 -format full_clock_expanded
puts "GROUP sw_ack min BC"
report_checks -from [get_ports {sw_ack*}] -path_delay min -corner BC -group_count 1 -endpoint_count 1 -format full_clock_expanded
puts "GROUP pg_ready max WC"
report_checks -to [get_ports {pg_ready*}] -path_delay max -corner WC -group_count 1 -endpoint_count 1 -format full_clock_expanded
puts "GROUP pg_ready min BC"
report_checks -to [get_ports {pg_ready*}] -path_delay min -corner BC -group_count 1 -endpoint_count 1 -format full_clock_expanded
puts "GROUP pg_late max WC"
report_checks -to [get_ports {pg_late*}] -path_delay max -corner WC -group_count 1 -endpoint_count 1 -format full_clock_expanded
puts "GROUP pg_late min BC"
report_checks -to [get_ports {pg_late*}] -path_delay min -corner BC -group_count 1 -endpoint_count 1 -format full_clock_expanded
puts "GROUP pg_fault max WC"
report_checks -to [get_ports {pg_fault*}] -path_delay max -corner WC -group_count 1 -endpoint_count 1 -format full_clock_expanded
puts "GROUP pg_fault min BC"
report_checks -to [get_ports {pg_fault*}] -path_delay min -corner BC -group_count 1 -endpoint_count 1 -format full_clock_expanded
puts "GROUP sw_en max WC"
report_checks -to [get_ports {sw_en*}] -path_delay max -corner WC -group_count 1 -endpoint_count 1 -format full_clock_expanded
puts "GROUP sw_en min BC"
report_checks -to [get_ports {sw_en*}] -path_delay min -corner BC -group_count 1 -endpoint_count 1 -format full_clock_expanded
