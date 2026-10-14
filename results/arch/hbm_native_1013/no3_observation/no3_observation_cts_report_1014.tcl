foreach l [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*RVT_FF*] {read_liberty $l}
foreach l [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*_LVT_FF_* /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*_SLVT_FF_*] {if {![string match *FAKE* $l]} {read_liberty $l}}
read_db /base/4_cts.odb
read_sdc /base/4_cts.sdc
source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl
estimate_parasitics -placement
read_sdc /src/physical/ref_tile/hbm_native_no3_observation_hub_m5_1014/signoff.sdc
puts "NO3_RETAINED_ROUTE_DIAGNOSTIC actual_source_074237148_CTS_placement_parasitics no_new_parent_adoption"
unset_output_delay [get_ports fclk_observe]
create_generated_clock -name observation_clock_probe -source [get_ports clk_sm] -divide_by 1 [get_ports fclk_observe]
set_propagated_clock [all_clocks]
sta::worst_slack_cmd max
report_units
report_clock_properties [all_clocks]
foreach n {clk_sm fclk_observe} {
 set p [get_ports $n]
 foreach prop {arrival_min_rise arrival_max_rise arrival_min_fall arrival_max_fall slew_min_rise slew_max_rise slew_min_fall slew_max_fall} {
  if {[catch {get_property $p $prop} v]} {puts "OBS_PROP_UNAVAILABLE $n $prop $v"} else {puts "OBS_PROP $n $prop $v"}
 }
 set bt [[ord::get_db_block] findBTerm $n];set net [$bt getNet]
 report_net -digits 6 [$net getName]
}
report_check_types -min_pulse_width -max_slew -max_capacitance
report_checks -unconstrained -from [get_ports clk_sm] -to [get_ports fclk_observe] -path_delay max -format full_clock_expanded -digits 5
report_checks -unconstrained -from [get_ports clk_sm] -to [get_ports fclk_observe] -path_delay min -format full_clock_expanded -digits 5
puts "OBS_PORT_PIN_API [info commands sta::*port*pin*]"
foreach p [get_pins output686/Y] {
 foreach prop {arrival_min_rise arrival_max_rise arrival_min_fall arrival_max_fall} {puts "OBS_DRIVER [get_full_name $p] $prop [get_property $p $prop]"}
}
if {[llength [info commands sta::get_port_pin]]} {
 set p [sta::get_port_pin [get_ports fclk_observe]]
 foreach prop {arrival_min_rise arrival_max_rise arrival_min_fall arrival_max_fall} {if {[catch {get_property $p $prop} v]} {puts "OBS_OUTPUT_PIN_UNAVAILABLE $prop $v"} else {puts "OBS_OUTPUT_PIN $prop $v"}}
}
exit
