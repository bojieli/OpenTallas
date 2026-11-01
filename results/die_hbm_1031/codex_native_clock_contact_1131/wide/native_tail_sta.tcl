set P /OpenROAD-flow-scripts/flow/platforms/asap7
foreach f [glob $P/lib/NLDM/*RVT_$::env(CORNER)_nldm*.lib*] {read_liberty $f}
set lc [string tolower $::env(CORNER)]
read_liberty /o/ot_hbm_idx_tail_native_${lc}.lib
read_db /o/route.odb
read_spef /o/route.spef
create_clock -name core -period 833 [get_ports drive]
set_propagated_clock [all_clocks]
set_input_transition 40 [get_ports drive]
set_clock_uncertainty -setup 0 [get_clocks core]
set_clock_uncertainty -hold 25 [get_clocks core]
report_checks -unconstrained -path_delay max -group_path_count 1
set fp [open /o/native_arr_$::env(CORNER).txt w]
foreach name {b5607/A b5607/Y native_tail/clk} {
    set p [get_pins $name]
    puts $fp "$name [get_property $p arrival_max_rise] [get_property $p arrival_min_rise] [get_property $p slew_max_rise] [get_property $p arrival_max_fall] [get_property $p arrival_min_fall] [get_property $p slew_max_fall]"
}
close $fp
puts OT_NATIVE_CLOCK_PIN_READOUT_DONE
