puts "PROBE_BEGIN FF_MIN"
report_checks -path_delay min -group_path_count 40 -endpoint_path_count 1 -format full_clock_expanded -digits 2 -path_group clk
puts "PROBE_END"
