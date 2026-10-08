# Supplemental observation only: source after the unchanged strict corner setup.
# Does not add/remove clocks, delays, exceptions, or uncertainty.
sta::worst_slack_cmd max
sta::worst_slack_cmd min
foreach p [get_ports *] {
    set n [get_full_name $p]
    set vals {}
    foreach prop {arrival_max_rise arrival_max_fall arrival_min_rise arrival_min_fall slack_max slack_min} {
        if {[catch {get_property $p $prop} value]} { set value "UNAVAILABLE" }
        lappend vals $prop $value
    }
    puts [list OT_PORT $n {*}$vals]
}
report_checks -path_delay min -group_path_count 30 -format full_clock_expanded
report_checks -path_delay max -group_path_count 30 -format full_clock_expanded
puts "OT_PORT_QUAL_DONE"
