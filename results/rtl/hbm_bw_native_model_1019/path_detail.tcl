source /src/tools/ref_tile/path_classes.tcl
report_checks -path_delay max -group_path_count 5 -endpoint_path_count 1 -format full_clock_expanded -fields {slew cap input net fanout} -digits 4 > /evidence/out/paths_tt_max.txt
report_checks -path_delay min -group_path_count 5 -endpoint_path_count 1 -format full_clock_expanded -fields {slew cap input net fanout} -digits 4 > /evidence/out/paths_tt_min.txt
exit
