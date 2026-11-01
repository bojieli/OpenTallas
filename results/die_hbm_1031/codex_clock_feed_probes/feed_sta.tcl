set P /OpenROAD-flow-scripts/flow/platforms/asap7
foreach f [glob $P/lib/NLDM/*RVT_$::env(CORNER)_nldm*.lib*] {read_liberty $f}
read_db /o/route.odb
read_spef /o/route.spef
create_clock -name vclk -period 833.0
set_input_delay 0 -clock vclk [get_ports drive]
set_input_transition 40 [get_ports drive]
set_load 3.0 [get_ports -quiet mesh_root]
report_checks -unconstrained -path_delay max -group_path_count 1
set fh [open /o/arr_$::env(CORNER).txt w]
foreach c [get_cells *] {
 foreach pn {A Y} {
  set p [get_pins [get_full_name $c]/$pn]
  puts $fh "$pn [get_full_name $c] [get_property $p arrival_max_rise] [get_property $p arrival_min_rise] [get_property $p slew_max_rise] [get_property $p arrival_max_fall] [get_property $p arrival_min_fall] [get_property $p slew_max_fall]"
 }
}
foreach p [get_ports -quiet mesh_root] {puts $fh "PORT mesh_root [get_property $p arrival_max_rise] [get_property $p arrival_min_rise] [get_property $p slew_max_rise] [get_property $p arrival_max_fall] [get_property $p arrival_min_fall] [get_property $p slew_max_fall]"}
close $fh
puts OT_FEED_STA_DONE
