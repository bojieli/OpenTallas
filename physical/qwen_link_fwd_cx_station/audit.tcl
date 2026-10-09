set_propagated_clock [all_clocks]
if {[llength [all_clocks]]!=4} {error "clock count changed"}
report_clock_properties [all_clocks]
foreach c {fclk_ab fclk_ba} {
 report_checks -to [all_registers -clock $c -data_pins] -path_delay min_max -group_path_count 4 -format full_clock_expanded
}
foreach p {ab_o ba_o} {
 report_checks -to [get_ports ${p}*] -path_delay min_max -group_path_count 2 -format full_clock_expanded
}
source /src/physical/qwen_link_fwd_cx_station/reset_inventory.tcl
puts "CX_STATION_AUDIT_OK"
