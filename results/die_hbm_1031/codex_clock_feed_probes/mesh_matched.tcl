set P /OpenROAD-flow-scripts/flow/platforms/asap7
foreach f [glob $P/lib/NLDM/*RVT_$::env(CORNER)_nldm*.lib*] {read_liberty $f}
read_lef $P/lef/asap7_tech_1x_201209.lef
read_lef $P/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_def /mesh/pilot.def
read_spef /mesh/drt.spef
create_clock -name vclk -period 833.0
set_input_delay 0 -clock vclk [get_ports root]
set_input_transition -rise $::env(ROOT_RISE) [get_ports root]
set_input_transition -fall $::env(ROOT_FALL) [get_ports root]
foreach c [get_cells M*] {set_disable_timing $c}
report_checks -unconstrained -path_delay max -group_path_count 1
set fh [open /out/tree_drt_$::env(CORNER).txt w]
set bh [open /out/both_$::env(CORNER).txt w]
foreach c [get_cells *] {
 set n [get_full_name $c]
 if {[string match L_* $n]} {set pins {A}} else {set pins {A Y}}
 foreach pn $pins {
  set p [get_pins $n/$pn]
  set rr "[get_property $p arrival_max_rise] [get_property $p arrival_min_rise] [get_property $p slew_max_rise]"
  puts $fh "$pn $n $rr"
  puts $bh "$pn $n $rr [get_property $p arrival_max_fall] [get_property $p arrival_min_fall] [get_property $p slew_max_fall]"
 }
}
close $fh;close $bh
puts OT_MATCHED_MESH_TREE_DONE
