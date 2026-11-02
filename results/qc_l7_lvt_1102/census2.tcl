source /work/postcts_gate.tcl
set paths [find_timing_paths -path_delay max -slack_max 0 -group_path_count 1000000 -endpoint_path_count 1 -unique_paths_to_endpoint -sort_by_slack]
set f [open /work/negative_endpoints.tsv w]
puts $f "start\tendpoint\tslack_native_property"
foreach path $paths {
 puts $f "[get_full_name [get_property $path startpoint]]\t[get_full_name [get_property $path endpoint]]\t[get_property $path slack]"
}
close $f
puts "L7_COMPLETE_NEGATIVE_ENDPOINT_COUNT [llength $paths]"
report_worst_slack -max
report_tns -max
report_checks -path_delay max -slack_max 0 -group_path_count 20 -format full_clock_expanded -digits 6 -fields {slew cap fanout}
puts L7_READ_ONLY_NEGATIVE_CENSUS_COMPLETE
