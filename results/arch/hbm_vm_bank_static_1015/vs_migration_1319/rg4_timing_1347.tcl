source /src/tools/ref_tile/path_classes.tcl
report_checks -path_delay max -group_path_count 8 -endpoint_path_count 1 -format full_clock_expanded -fields {slew capacitance fanout input_pin nets} -digits 3
exit
