puts "ATTR_WS [sta::worst_slack_cmd max]"
puts "ATTR_TNS [sta::total_negative_slack_cmd max]"
set negative {}
set output_count 0
foreach p [all_outputs] {
 incr output_count
 set s [get_property $p slack_max]
 if {$s ne "INF" && $s < 0} {lappend negative [list $s $p [get_full_name $p]]}
}
puts "ATTR_OUTPUT_COUNT $output_count NEGATIVE_PROPERTY_COUNT [llength $negative]"
set ordered [lsort -real -index 0 $negative]
foreach item [lrange $ordered 0 7] {
 lassign $item s p name
 puts "ATTR_NEGATIVE_PORT_BEGIN name=$name property_slack_max=$s"
 puts "ATTR_PORT_OBJECT $p"
 set paths [find_timing_paths -to $p -path_delay max -group_path_count 2]
 puts "ATTR_CONSTRAINED_PATH_COUNT [llength $paths]"
 foreach path $paths {puts "ATTR_CONSTRAINED_PATH_SLACK [get_property $path slack]"}
 report_checks -to $p -path_delay max -group_path_count 2 -format full_clock_expanded
 puts "ATTR_UNCONSTRAINED_DIAGNOSTIC"
 report_checks -to $p -path_delay max -unconstrained -group_path_count 2 -format full_clock_expanded
 puts "ATTR_NEGATIVE_PORT_END"
}
puts "ATTR_ACTUAL_OUTPUT_PATHS"
report_checks -to [all_outputs] -path_delay max -group_path_count 2 -format full_clock_expanded
puts "ATTR_CLOCKS"
report_clocks
puts "ATTR_DONE"
exit
