source /work/postcts_gate.tcl
puts L7_ACTUAL_CRITICAL_PATHS_BEGIN
set mode [expr {$::env(OT_CORNER) eq "TT" ? "max" : "min"}]
report_checks -path_delay $mode -group_path_count 5 -format full_clock_expanded -digits 6 -fields {slew cap fanout}
puts L7_ACTUAL_CRITICAL_PATHS_END
