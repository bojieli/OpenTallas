source /out/prefix.tcl
report_checks -path_delay min -group_path_count 16 -endpoint_path_count 1 -format full_clock_expanded -fields {fanout cap slew input_pin} -digits 3 > /out/worst16_ff.rpt
set f [open /out/negative_paths.tsv w]
puts $f "slack_ps\tstart\tend\tlaunch_clock\tcapture_clock"
foreach p [find_timing_paths -path_delay min -group_path_count 200000 -endpoint_path_count 1 -slack_max 0] {
 set sp [get_property $p startpoint];set ep [get_property $p endpoint]
 set sc [get_property $p startpoint_clock];set ec [get_property $p endpoint_clock];set sn {};set en {};catch {set sn [get_name $sc]};catch {set en [get_name $ec]}
 puts $f "[get_property $p slack]\t[get_full_name $sp]\t[get_full_name $ep]\t$sn\t$en"
}
close $f
puts "ACTUAL_FF_WNS [sta::time_sta_ui [sta::worst_slack_cmd min]] ENDPOINTS [sta::endpoint_violation_count min]"
exit
