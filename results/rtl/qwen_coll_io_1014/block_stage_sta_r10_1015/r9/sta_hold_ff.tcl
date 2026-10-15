read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef
foreach l {/w/lib/asap7sc7p5t_AO_RVT_FF_nldm_211120.lib /w/lib/asap7sc7p5t_INVBUF_RVT_FF_nldm_220122.lib /w/lib/asap7sc7p5t_OA_RVT_FF_nldm_211120.lib /w/lib/asap7sc7p5t_SIMPLE_RVT_FF_nldm_211120.lib /w/lib/asap7sc7p5t_SEQ_RVT_FF_nldm_220123.lib} {read_liberty $l}
read_verilog /w/net.v
link_design gearbox_sta
read_sdc /w/clocks.sdc
report_clock_properties
puts "PAIR core core"
report_checks -from [get_clocks core] -to [get_clocks core] -path_delay min -format full_clock_expanded -digits 3 -group_path_count 1
puts "PAIR core fdi"
report_checks -from [get_clocks core] -to [get_clocks fdi] -path_delay min -format full_clock_expanded -digits 3 -group_path_count 1
puts "PAIR core rx0"
report_checks -from [get_clocks core] -to [get_clocks rx0] -path_delay min -format full_clock_expanded -digits 3 -group_path_count 1
puts "PAIR core rx1"
report_checks -from [get_clocks core] -to [get_clocks rx1] -path_delay min -format full_clock_expanded -digits 3 -group_path_count 1
puts "PAIR core rx2"
report_checks -from [get_clocks core] -to [get_clocks rx2] -path_delay min -format full_clock_expanded -digits 3 -group_path_count 1
puts "PAIR fdi core"
report_checks -from [get_clocks fdi] -to [get_clocks core] -path_delay min -format full_clock_expanded -digits 3 -group_path_count 1
puts "PAIR fdi fdi"
report_checks -from [get_clocks fdi] -to [get_clocks fdi] -path_delay min -format full_clock_expanded -digits 3 -group_path_count 1
puts "PAIR fdi rx0"
report_checks -from [get_clocks fdi] -to [get_clocks rx0] -path_delay min -format full_clock_expanded -digits 3 -group_path_count 1
puts "PAIR fdi rx1"
report_checks -from [get_clocks fdi] -to [get_clocks rx1] -path_delay min -format full_clock_expanded -digits 3 -group_path_count 1
puts "PAIR fdi rx2"
report_checks -from [get_clocks fdi] -to [get_clocks rx2] -path_delay min -format full_clock_expanded -digits 3 -group_path_count 1
puts "PAIR rx0 core"
report_checks -from [get_clocks rx0] -to [get_clocks core] -path_delay min -format full_clock_expanded -digits 3 -group_path_count 1
puts "PAIR rx0 fdi"
report_checks -from [get_clocks rx0] -to [get_clocks fdi] -path_delay min -format full_clock_expanded -digits 3 -group_path_count 1
puts "PAIR rx0 rx0"
report_checks -from [get_clocks rx0] -to [get_clocks rx0] -path_delay min -format full_clock_expanded -digits 3 -group_path_count 1
puts "PAIR rx0 rx1"
report_checks -from [get_clocks rx0] -to [get_clocks rx1] -path_delay min -format full_clock_expanded -digits 3 -group_path_count 1
puts "PAIR rx0 rx2"
report_checks -from [get_clocks rx0] -to [get_clocks rx2] -path_delay min -format full_clock_expanded -digits 3 -group_path_count 1
puts "PAIR rx1 core"
report_checks -from [get_clocks rx1] -to [get_clocks core] -path_delay min -format full_clock_expanded -digits 3 -group_path_count 1
puts "PAIR rx1 fdi"
report_checks -from [get_clocks rx1] -to [get_clocks fdi] -path_delay min -format full_clock_expanded -digits 3 -group_path_count 1
puts "PAIR rx1 rx0"
report_checks -from [get_clocks rx1] -to [get_clocks rx0] -path_delay min -format full_clock_expanded -digits 3 -group_path_count 1
puts "PAIR rx1 rx1"
report_checks -from [get_clocks rx1] -to [get_clocks rx1] -path_delay min -format full_clock_expanded -digits 3 -group_path_count 1
puts "PAIR rx1 rx2"
report_checks -from [get_clocks rx1] -to [get_clocks rx2] -path_delay min -format full_clock_expanded -digits 3 -group_path_count 1
puts "PAIR rx2 core"
report_checks -from [get_clocks rx2] -to [get_clocks core] -path_delay min -format full_clock_expanded -digits 3 -group_path_count 1
puts "PAIR rx2 fdi"
report_checks -from [get_clocks rx2] -to [get_clocks fdi] -path_delay min -format full_clock_expanded -digits 3 -group_path_count 1
puts "PAIR rx2 rx0"
report_checks -from [get_clocks rx2] -to [get_clocks rx0] -path_delay min -format full_clock_expanded -digits 3 -group_path_count 1
puts "PAIR rx2 rx1"
report_checks -from [get_clocks rx2] -to [get_clocks rx1] -path_delay min -format full_clock_expanded -digits 3 -group_path_count 1
puts "PAIR rx2 rx2"
report_checks -from [get_clocks rx2] -to [get_clocks rx2] -path_delay min -format full_clock_expanded -digits 3 -group_path_count 1
puts "PAIR all all"
report_checks -path_delay min -digits 3 -group_path_count 1
puts "STA_DONE"
