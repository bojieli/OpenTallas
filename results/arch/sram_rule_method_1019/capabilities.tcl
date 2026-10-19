puts "VERSION [ord::openroad_version]"
foreach cmd {check_drc pin_access detailed_route detailed_route_debug check_power_grid pdngen add_global_connection global_connect} {
 puts "COMMAND $cmd present=[llength [info commands $cmd]]"
 catch {help $cmd} result
 puts $result
}
exit
