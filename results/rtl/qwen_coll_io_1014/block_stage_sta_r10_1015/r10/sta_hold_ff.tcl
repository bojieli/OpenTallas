read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef
foreach l {/w/lib/asap7sc7p5t_AO_RVT_FF_nldm_211120.lib /w/lib/asap7sc7p5t_INVBUF_RVT_FF_nldm_220122.lib /w/lib/asap7sc7p5t_OA_RVT_FF_nldm_211120.lib /w/lib/asap7sc7p5t_SIMPLE_RVT_FF_nldm_211120.lib /w/lib/asap7sc7p5t_SEQ_RVT_FF_nldm_220123.lib} {read_liberty $l}
read_verilog /w/net.v
link_design gearbox_sta
read_sdc /w/clocks.sdc
report_clock_properties
puts "PAIR blk0 blk0"
report_checks -from [get_clocks blk0] -to [get_clocks blk0] -path_delay min -format full_clock_expanded -digits 3 -group_path_count 1
puts "PAIR blk0 blk1"
report_checks -from [get_clocks blk0] -to [get_clocks blk1] -path_delay min -format full_clock_expanded -digits 3 -group_path_count 1
puts "PAIR blk0 core"
report_checks -from [get_clocks blk0] -to [get_clocks core] -path_delay min -format full_clock_expanded -digits 3 -group_path_count 1
puts "PAIR blk0 fdi"
report_checks -from [get_clocks blk0] -to [get_clocks fdi] -path_delay min -format full_clock_expanded -digits 3 -group_path_count 1
puts "PAIR blk0 fdirx"
report_checks -from [get_clocks blk0] -to [get_clocks fdirx] -path_delay min -format full_clock_expanded -digits 3 -group_path_count 1
puts "PAIR blk1 blk0"
report_checks -from [get_clocks blk1] -to [get_clocks blk0] -path_delay min -format full_clock_expanded -digits 3 -group_path_count 1
puts "PAIR blk1 blk1"
report_checks -from [get_clocks blk1] -to [get_clocks blk1] -path_delay min -format full_clock_expanded -digits 3 -group_path_count 1
puts "PAIR blk1 core"
report_checks -from [get_clocks blk1] -to [get_clocks core] -path_delay min -format full_clock_expanded -digits 3 -group_path_count 1
puts "PAIR blk1 fdi"
report_checks -from [get_clocks blk1] -to [get_clocks fdi] -path_delay min -format full_clock_expanded -digits 3 -group_path_count 1
puts "PAIR blk1 fdirx"
report_checks -from [get_clocks blk1] -to [get_clocks fdirx] -path_delay min -format full_clock_expanded -digits 3 -group_path_count 1
puts "PAIR core blk0"
report_checks -from [get_clocks core] -to [get_clocks blk0] -path_delay min -format full_clock_expanded -digits 3 -group_path_count 1
puts "PAIR core blk1"
report_checks -from [get_clocks core] -to [get_clocks blk1] -path_delay min -format full_clock_expanded -digits 3 -group_path_count 1
puts "PAIR core core"
report_checks -from [get_clocks core] -to [get_clocks core] -path_delay min -format full_clock_expanded -digits 3 -group_path_count 1
puts "PAIR core fdi"
report_checks -from [get_clocks core] -to [get_clocks fdi] -path_delay min -format full_clock_expanded -digits 3 -group_path_count 1
puts "PAIR core fdirx"
report_checks -from [get_clocks core] -to [get_clocks fdirx] -path_delay min -format full_clock_expanded -digits 3 -group_path_count 1
puts "PAIR fdi blk0"
report_checks -from [get_clocks fdi] -to [get_clocks blk0] -path_delay min -format full_clock_expanded -digits 3 -group_path_count 1
puts "PAIR fdi blk1"
report_checks -from [get_clocks fdi] -to [get_clocks blk1] -path_delay min -format full_clock_expanded -digits 3 -group_path_count 1
puts "PAIR fdi core"
report_checks -from [get_clocks fdi] -to [get_clocks core] -path_delay min -format full_clock_expanded -digits 3 -group_path_count 1
puts "PAIR fdi fdi"
report_checks -from [get_clocks fdi] -to [get_clocks fdi] -path_delay min -format full_clock_expanded -digits 3 -group_path_count 1
puts "PAIR fdi fdirx"
report_checks -from [get_clocks fdi] -to [get_clocks fdirx] -path_delay min -format full_clock_expanded -digits 3 -group_path_count 1
puts "PAIR fdirx blk0"
report_checks -from [get_clocks fdirx] -to [get_clocks blk0] -path_delay min -format full_clock_expanded -digits 3 -group_path_count 1
puts "PAIR fdirx blk1"
report_checks -from [get_clocks fdirx] -to [get_clocks blk1] -path_delay min -format full_clock_expanded -digits 3 -group_path_count 1
puts "PAIR fdirx core"
report_checks -from [get_clocks fdirx] -to [get_clocks core] -path_delay min -format full_clock_expanded -digits 3 -group_path_count 1
puts "PAIR fdirx fdi"
report_checks -from [get_clocks fdirx] -to [get_clocks fdi] -path_delay min -format full_clock_expanded -digits 3 -group_path_count 1
puts "PAIR fdirx fdirx"
report_checks -from [get_clocks fdirx] -to [get_clocks fdirx] -path_delay min -format full_clock_expanded -digits 3 -group_path_count 1
puts "PAIR all all"
report_checks -path_delay min -digits 3 -group_path_count 1
puts "STA_DONE"
