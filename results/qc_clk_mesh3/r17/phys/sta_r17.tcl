# INFRA-FIRST-QC-R17: clock_routed sta.tcl with the explicit-cell names (ckt_*): every BUFx24 A/Y + every tap port t_*
foreach f [glob $::env(LIBDIR)/*RVT_$::env(CORNER)_nldm*.lib*] { read_liberty $f }
read_db /out/routed.odb
read_spef /out/$::env(BASIS).spef
create_clock -name vclk -period 833.000
set_driving_cell -lib_cell BUFx24_ASAP7_75t_R -pin Y [get_ports root]
set_input_delay 0 -clock vclk [get_ports root]
set_load 3.0 [get_ports t_*]
set_output_delay 0 -clock vclk [get_ports t_*]
report_checks -path_delay min_max -format end
set fh [open /out/r17_tree_$::env(CORNER)_$::env(BASIS).txt w]
foreach c [get_cells ckt_*] {
  set a [get_pins [get_full_name $c]/A]; set y [get_pins [get_full_name $c]/Y]
  puts $fh "N [get_full_name $c] [get_property $y arrival_max_rise] [get_property $y arrival_min_rise] [get_property $y slew_max_rise] [get_property $a arrival_max_rise] [get_property $a slew_max_rise]"
}
foreach p [get_ports t_*] {
  set e [catch {set am [get_property $p arrival_max_rise]; set an [get_property $p arrival_min_rise]; set s [get_property $p slew_max_rise]}]
  if {$e} { puts $fh "T [get_full_name $p] NA" } else { puts $fh "T [get_full_name $p] $am $an $s" }
}
close $fh
report_check_types -max_slew -max_capacitance -violators
puts OT_DONE
