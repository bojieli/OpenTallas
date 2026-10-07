set P /OpenROAD-flow-scripts/flow/platforms/asap7
foreach l [glob $P/lib/NLDM/*RVT_$::env(CORNER)*] {read_liberty $l}
read_db /base/4_1_cts.odb
read_sdc /input/station.sdc
source $P/setRC.tcl
set_propagated_clock [all_clocks]
estimate_parasitics -placement
report_checks -path_delay min -group_path_count 3 -format full_clock_expanded -digits 3
report_checks -path_delay max -group_path_count 1 -format full_clock_expanded -digits 3
report_checks -path_delay min -to [get_pins _303244_/D] -format full_clock_expanded -digits 3
puts "DIAG_DONE $::env(CORNER)"
