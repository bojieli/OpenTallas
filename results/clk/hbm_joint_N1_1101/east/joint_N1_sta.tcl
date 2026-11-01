set P /OpenROAD-flow-scripts/flow/platforms/asap7
foreach f [glob $P/lib/NLDM/*RVT_$::env(CORNER)_nldm*.lib*] {read_liberty $f}
read_db /o/route.odb
read_spef /o/route.spef
create_clock -name core -period 833 [get_ports drive0]
set_input_transition 40 [get_ports drive0]
set_clock_uncertainty -setup 0 [get_clocks core]
set_clock_uncertainty -hold 25 [get_clocks core]
# Actual two-driver mesh is an analog boundary: measure its real source A pins.
set_disable_timing [get_cells {M0_0 M0_1}]
set_propagated_clock [all_clocks]
report_checks -unconstrained -path_delay max -group_path_count 1
set fp [open /o/joint_N1_arr_$::env(CORNER).txt w]
foreach name {N1/A N1/Y M0_0/A M0_1/A} {
 set p [get_pins $name]
 puts $fp "$name [get_property $p arrival_max_rise] [get_property $p arrival_min_rise] [get_property $p slew_max_rise] [get_property $p arrival_max_fall] [get_property $p arrival_min_fall] [get_property $p slew_max_fall]"
}
close $fp
puts OT_ACTUAL_N1_FANOUT_READOUT_DONE
