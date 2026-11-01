set P /OpenROAD-flow-scripts/flow/platforms/asap7
foreach f [glob $P/lib/NLDM/*RVT_$::env(CORNER)_nldm*.lib*] {read_liberty $f}
read_db /new/route.odb
read_spef /new/route.spef
create_clock -name vclk -period 833.0
set_input_delay 0 -clock vclk [get_ports drive]
source /work/params_$::env(CORNER).tcl
set_input_transition -rise $trise [get_ports drive]
set_input_transition -fall $tfall [get_ports drive]
set_load 3.0 [get_ports -quiet mesh_root]
set_output_delay -max 0 -clock vclk [get_ports -quiet mesh_root]
set_output_delay -min 0 -clock vclk [get_ports -quiet mesh_root]
report_checks -unconstrained -path_delay max -group_path_count 1
set fh [open /work/new_arr_$::env(CORNER).txt w]
foreach c [get_cells *] {
 foreach pn {A Y} {
  set p [get_pins [get_full_name $c]/$pn]
  puts $fh "$pn [get_full_name $c] [get_property $p arrival_max_rise] [get_property $p arrival_min_rise] [get_property $p slew_max_rise] [get_property $p arrival_max_fall] [get_property $p arrival_min_fall] [get_property $p slew_max_fall]"
 }
}
foreach p [get_ports -quiet mesh_root] {puts $fh "PORT mesh_root [expr {833.0 - [get_property $p slack_max_rise]}] [get_property $p slack_min_rise] [get_property $p slew_max_rise] [expr {833.0 - [get_property $p slack_max_fall]}] [get_property $p slack_min_fall] [get_property $p slew_max_fall]"}
close $fh
puts OT_FEED_STA_DONE
