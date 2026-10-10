source /OpenROAD-flow-scripts/flow/scripts/load.tcl
load_design 1_synth.odb 1_synth.sdc
puts {CE_B_RESET_CONE_BEGIN}
set block [[ord::get_db] getChip]
set block [$block getBlock]
foreach net [$block getNets] {
 if {[string match {*erst_n*} [$net getName]]} {puts "RESET_NET [$net getName] ITERM_COUNT [llength [$net getITerms]]"}
}
report_checks -path_delay max -group_count 5 -endpoint_count 1 -format full_clock_expanded -fields {slew cap fanout input_pin nets}
puts {CE_B_RESET_CONE_END}
exit
