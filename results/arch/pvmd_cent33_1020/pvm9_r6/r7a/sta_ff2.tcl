set P /OpenROAD-flow-scripts/flow/platforms/asap7
foreach l [glob $P/lib/NLDM/*RVT_FF*] { read_liberty $l }
read_liberty $::env(R7_MACRO_LIB)
read_db $::env(R7_ODB)
read_sdc $::env(R7_SDC)
create_clock -name core_clk -period 833.333 [get_ports clk]
set_clock_uncertainty -setup 60 [all_clocks]; set_clock_uncertainty -hold 25 [all_clocks]
set_propagated_clock [all_clocks]
source $P/setRC.tcl
estimate_parasitics -global_routing
foreach {nm fr} [list reg [all_registers -clock_pins] in [all_inputs -no_clocks]] {
  set ps [find_timing_paths -path_delay min -from $fr -to [all_registers -data_pins] -group_path_count 2000 -endpoint_path_count 1 -slack_max 0]
  set n [llength $ps]; set w ""
  if {$n} {set w [get_property [lindex $ps 0] slack]}
  puts "R7_FF_HOLD from=$nm violating_endpoints=$n worst=$w"
  set k 0; foreach p $ps { if {$k>=6} break; incr k; puts "R7_FF_PATH $nm [get_property $p slack] [get_full_name [get_property $p startpoint]] -> [get_full_name [get_property $p endpoint]]" }
}
report_checks -path_delay min -from [all_registers -clock_pins] -to [all_registers -data_pins] -group_path_count 1 -fields {slew cap}
