
set P /OpenROAD-flow-scripts/flow/platforms/asap7
foreach f [lsort [glob $P/lib/NLDM/*_RVT_$::env(LIBC)_*.lib*]] {read_liberty $f}
read_db $::env(ODB)
read_sdc $::env(SDC)
read_spef $::env(SPEF)
set_propagated_clock [all_clocks]
puts LATBEGIN
report_clock_latency -clock clk_sm -digits 2
puts LATEND
foreach {tag from to} {reg2reg all_registers all_registers in2reg all_inputs all_registers reg2out all_registers all_outputs} {
 foreach d {max min} {
  set paths [find_timing_paths -path_delay $d -from [$from] -to [$to] -group_path_count 1]
  if {[llength $paths]} {puts "SLACK $tag $d [format %.2f [get_property [lindex $paths 0] slack]]"} else {puts "SLACK $tag $d none"}
 }
}
puts "WORST max [format %.2f [sta::worst_slack -max]]"
puts "WORST min [format %.2f [sta::worst_slack -min]]"
report_checks -path_delay max -group_path_count 8 -format full_clock_expanded -digits 2
report_checks -path_delay min -group_path_count 8 -format full_clock_expanded -digits 2
# Include async reset recovery/removal alongside ordinary data paths; never false-path resets.
report_check_types -recovery -removal -violators -digits 2
report_checks -from [get_ports por_n] -path_delay max -group_path_count 4 -format full_clock_expanded -digits 2
report_checks -from [get_ports por_n] -path_delay min -group_path_count 4 -format full_clock_expanded -digits 2
