set P /OpenROAD-flow-scripts/flow/platforms/asap7
foreach f [glob $P/lib/NLDM/*RVT_$::env(CORNER)_nldm*.lib*] {read_liberty $f}
read_db /o/route.odb
read_spef /o/route.spef
create_clock -name core -period 833 [get_ports drive]
set_propagated_clock [all_clocks]
source /o/params_$::env(CORNER).tcl
set_input_transition -rise $trise [get_ports drive]
set_input_transition -fall $tfall [get_ports drive]
report_checks -unconstrained -path_delay max -group_path_count 1
set fh [open /o/joint_arr_$::env(CORNER).txt w]
foreach cell [get_cells *] {
 foreach pin [get_pins -of_objects $cell] {
  set n [get_full_name $pin]
  puts $fh "$n [get_property $pin arrival_max_rise] [get_property $pin arrival_min_rise] [get_property $pin slew_max_rise] [get_property $pin arrival_max_fall] [get_property $pin arrival_min_fall] [get_property $pin slew_max_fall]"
 }
}
close $fh
puts OT_JOINT_CLOCK_STA_DONE
