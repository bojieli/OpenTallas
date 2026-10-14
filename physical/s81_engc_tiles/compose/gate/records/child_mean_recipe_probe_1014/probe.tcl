set C $::env(CORNER)
set P /OpenROAD-flow-scripts/flow/platforms/asap7
foreach l [glob $P/lib/NLDM/*RVT_${C}*] { read_liberty $l }
read_db /base/6_final.odb
read_sdc /base/6_final.sdc
read_spef /base/6_final.spef
read_sdc /recipe/child_mean.sdc
puts "CHILD_RECIPE_PROBE $C core_period=[get_property [get_clocks core_clk] period]"
report_worst_slack -max
report_worst_slack -min
write_sdc /tmp/child_probe.sdc
set f [open /tmp/child_probe.sdc r]
foreach line [split [read $f] "\n"] {
 if {[regexp {^(create_clock|set_clock_latency|set_input_transition)} $line]} {puts "SOURCE_CONTEXT $line"}
}
close $f
puts "CHILD_RECIPE_DONE $C"
