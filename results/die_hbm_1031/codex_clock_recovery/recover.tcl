set P /OpenROAD-flow-scripts/flow/platforms/asap7
read_lef $P/lef/asap7_tech_1x_201209.lef
read_lef $P/lef/asap7sc7p5t_28_R_1x_220121a.lef
foreach f [glob $P/lib/NLDM/*RVT_$::env(CORNER)_nldm*.lib*] {read_liberty $f}
read_def /i/pilot.def
create_clock -name vclk -period 833.0
set_driving_cell -lib_cell BUFx24_ASAP7_75t_R -pin Y [get_ports root]
set_input_delay 0 -clock vclk [get_ports root]
foreach c [get_cells M*] {set_disable_timing $c}
read_spef /i/drt.spef
report_checks -unconstrained -path_delay max -group_path_count 1
set fh [open /o/tree_drt_$::env(CORNER).txt w]
set missing 0
foreach c [get_cells *] {
 set n [get_full_name $c]
 if {[string match L_* $n]} {set pins {A}} else {set pins {A Y}}
 foreach pn $pins {
  set p [get_pins -quiet $n/$pn]
  if {[llength $p] != 1} {puts "MISSING_PIN $n/$pn";incr missing;continue}
  puts $fh "$pn $n [get_property $p arrival_max_rise] [get_property $p arrival_min_rise] [get_property $p slew_max_rise]"
 }
}
close $fh
puts "OT_RECOVERY_DONE missing=$missing"
