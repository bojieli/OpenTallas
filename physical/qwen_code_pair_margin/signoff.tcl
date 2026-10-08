# Routed sign-off at the contract period: env LIBC (SS|FF), ODB, SPEF, SDC, MACROLIBS (space-separated).
set P /OpenROAD-flow-scripts/flow/platforms/asap7
foreach f [lsort [glob $P/lib/NLDM/*_RVT_$::env(LIBC)_*.lib*]] { read_liberty $f }
foreach f $::env(MACROLIBS) { read_liberty $f }
read_db $::env(ODB)
read_sdc $::env(SDC)
read_spef $::env(SPEF)
set_propagated_clock [all_clocks]
foreach {tag from to} {reg2reg all_registers all_registers in2reg all_inputs all_registers reg2out all_registers all_outputs} {
  foreach d {max min} {
    set paths [find_timing_paths -path_delay $d -from [$from] -to [$to] -group_path_count 1]
    if {[llength $paths]} {puts "SLACK $tag $d [format %.2f [get_property [lindex $paths 0] slack]]"} else {puts "SLACK $tag $d none"}
  }
}
puts "WORST max [format %.2f [sta::worst_slack -max]]"
puts "WORST min [format %.2f [sta::worst_slack -min]]"
puts "TNS max [format %.2f [sta::total_negative_slack -max]]"
report_checks -path_delay $::env(DELAY) -group_path_count 3 -format full_clock_expanded -digits 2
