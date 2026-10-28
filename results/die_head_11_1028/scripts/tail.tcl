# DIE-HEAD-11 duty probe: rise vs fall propagation through the BUF tree (input delay on root applies to both edges)
set fh [open /out/duty_$::env(CORNER).txt w]
foreach p [get_ports t_*] {
  set d ""
  foreach q [get_pins -of_objects [get_nets [get_full_name $p]]] { if {[get_property $q direction] eq "output"} { set d $q } }
  if {$d eq ""} { puts $fh "X [get_full_name $p]"; continue }
  puts $fh "P [get_full_name $p] [get_property $d arrival_max_rise] [get_property $d arrival_max_fall] [get_property $d arrival_min_rise] [get_property $d arrival_min_fall] [get_property $d slew_max_rise] [get_property $d slew_max_fall] [get_full_name $d]"
}
foreach i [get_cells ck_*] { set q [get_pins [get_full_name $i]/Y]; puts $fh "N [get_full_name $i] [get_property $q arrival_max_rise] [get_property $q arrival_max_fall]" }
close $fh
delete_clock [get_clocks vclk]
create_clock -name dck -period 833.333 -waveform {0 416.667} [get_ports root]
set_propagated_clock [get_clocks dck]
report_check_types -min_pulse_width -verbose > /out/mpw_$::env(CORNER).rpt
report_pulse_width_checks >> /out/mpw_$::env(CORNER).rpt
puts OT_DONE
