set P /OpenROAD-flow-scripts/flow/platforms/asap7
foreach f [glob $P/lib/NLDM/*RVT_$::env(CORNER)_nldm*.lib*] {read_liberty $f}
read_db /old/route.odb
read_spef /old/route.spef
create_clock -name vclk -period 833.0
set_input_delay 0 -clock vclk [get_ports drive]
source /work/targets_$::env(CORNER).tcl
proc measure {r f pin} {
 set_input_transition -rise $r [get_ports drive]
 set_input_transition -fall $f [get_ports drive]
 report_checks -unconstrained -path_delay max -group_path_count 1
 return [get_property [get_pins $::source/$pin] slew_max_rise]
}
set trise 40.0;set tfall 40.0
foreach {pin target which} [list A $target_A rise Y $target_Y fall] {
 set lo 0.01;set hi 240.0
 for {set i 0} {$i<13} {incr i} {
  set mid [expr {($lo+$hi)/2}]
  if {$which eq "rise"} {set v [measure $mid $tfall $pin]} else {set v [measure $trise $mid $pin]}
  if {$v<$target} {set lo $mid} else {set hi $mid}
 }
 if {$which eq "rise"} {set trise [expr {($lo+$hi)/2}]} else {set tfall [expr {($lo+$hi)/2}]}
}
measure $trise $tfall A
set ar [get_property [get_pins $source/A] slew_max_rise]
set yr [get_property [get_pins $source/Y] slew_max_rise]
if {abs($ar-$target_A)>0.1 || abs($yr-$target_Y)>0.1} {error "source waveform calibration failed: $ar/$target_A $yr/$target_Y"}
set q [open /work/params_$::env(CORNER).tcl w]
puts $q "set trise $trise\nset tfall $tfall";close $q
set q [open /work/calibration_$::env(CORNER).json w]
puts $q "{\"input_rise_ps\":$trise,\"input_fall_ps\":$tfall,\"source_A_rise_slew_ps\":$ar,\"source_Y_rise_slew_ps\":$yr,\"target_A_rise_slew_ps\":$target_A,\"target_Y_rise_slew_ps\":$target_Y}";close $q
set q [open /work/old_arr_$::env(CORNER).txt w]
foreach c [get_cells *] {foreach pn {A Y} {set p [get_pins [get_full_name $c]/$pn];puts $q "$pn [get_full_name $c] [get_property $p arrival_max_rise] [get_property $p arrival_min_rise] [get_property $p slew_max_rise] [get_property $p arrival_max_fall] [get_property $p arrival_min_fall] [get_property $p slew_max_fall]"}}
close $q
puts OT_SOURCE_WAVEFORM_CALIBRATED
