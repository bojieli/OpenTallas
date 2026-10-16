
foreach l [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*RVT_TT*] {read_liberty $l}
foreach l [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*_LVT_TT_* /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*_SLVT_TT_*] {if {![string match *FAKE* $l]} {read_liberty $l}}
read_db /base/6_final.odb
read_sdc /base/6_final.sdc
read_spef /base/6_final.spef
create_clock -name core_clk -period 833.333 [get_ports {ck[0]}]
create_clock -name ser_clk -period 1111.110667 [get_ports {ckv[0]}]
set_clock_uncertainty -setup 60 [get_clocks {core_clk ser_clk}]
set_clock_uncertainty -hold 25 [get_clocks {core_clk ser_clk}]
set_propagated_clock [all_clocks]
set_clock_latency -source -187.8 [get_clocks core_clk]
set_clock_latency -source -186.3 [get_clocks ser_clk]
report_clock_properties [all_clocks]
foreach pin {ck[0] ckv[0]} {
 foreach prop {slew_max_rise slew_min_rise} {
  puts "OT_CAPTURE_ROOT_SLEW $pin $prop [get_property [get_ports $pin] $prop]"
 }
}
foreach pair {{core_clk core_clk core core} {ser_clk ser_clk serial serial} {core_clk ser_clk core serial} {ser_clk core_clk serial core}} {
 lassign $pair launch capture a b
 foreach sense {max min} {
  set starts [all_registers -clock_pins -clock [get_clocks $launch]]
  set ends [all_registers -data_pins -clock [get_clocks $capture]]
  set found [find_timing_paths -from $starts -to $ends -path_delay $sense -group_path_count 1 -endpoint_path_count 1 -sort_by_slack]
  if {![llength $found]} {error "missing actual path $launch/$capture/$sense"}
  set p [lindex $found 0]
  puts "OT_CAPTURE_ARCHIVE_PHASE {\"corner\":\"tt\",\"launch\":\"$a\",\"capture\":\"$b\",\"sense\":\"$sense\",\"startpoint\":\"[get_full_name [get_property $p startpoint]]\",\"endpoint\":\"[get_full_name [get_property $p endpoint]]\",\"slack_ps\":[get_property $p slack]}"
  report_checks -from $starts -to $ends -path_delay $sense -format full_clock_expanded -fields {slew capacitance fanout} -group_path_count 1 -endpoint_path_count 1
 }
}
report_checks -path_delay min -format full_clock_expanded -group_path_count 3
exit
