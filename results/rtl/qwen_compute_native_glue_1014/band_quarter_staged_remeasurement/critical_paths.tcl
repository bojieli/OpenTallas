source /src/tools/ref_tile/path_classes.tcl
puts BAND_FULL_MAX_PATHS
report_checks -path_delay max -group_path_count 12 -endpoint_path_count 1 -format full_clock_expanded -fields {slew cap fanout input_pins nets} -digits 5
puts BAND_FULL_MIN_PATHS
report_checks -path_delay min -group_path_count 8 -endpoint_path_count 1 -format full_clock_expanded -fields {slew cap fanout input_pins nets} -digits 5
