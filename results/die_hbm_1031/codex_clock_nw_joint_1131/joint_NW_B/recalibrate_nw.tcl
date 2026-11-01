set P /OpenROAD-flow-scripts/flow/platforms/asap7
foreach f [glob $P/lib/NLDM/*RVT_$::env(CORNER)_nldm*.lib*] {read_liberty $f}
read_db /o/route.odb
read_spef /o/route.spef
create_clock -name vclk -period 833
set_input_delay 0 -clock vclk [get_ports drive]
source /o/target_boundary_$::env(CORNER).tcl
set trise $initial_rise
set tfall $initial_fall
foreach direction {rise fall} {
    set lo 0.01
    set hi 240.0
    for {set i 0} {$i < 15} {incr i} {
        set mid [expr {($lo+$hi)/2}]
        if {$direction eq "rise"} {set trise $mid} else {set tfall $mid}
        set_input_transition -rise $trise [get_ports drive]
        set_input_transition -fall $tfall [get_ports drive]
        report_checks -unconstrained -path_delay max -group_path_count 1
        set measured [get_property [get_pins $source/A] slew_max_$direction]
        set target [set target_$direction]
        if {$measured < $target} {set lo $mid} else {set hi $mid}
    }
}
# Preserve the original measured source-A boundary phase; only the artificial
# recut input-access wire changed. Never fit the newly loaded source-Y output.
foreach direction {rise fall} {
    foreach mode {max min} bound {late early} {
        set actual [get_property [get_pins $source/A] arrival_${mode}_${direction}]
        set desired [set old_A_${direction}_${bound}]
        set_input_delay -clock vclk -$direction -$mode [expr {$desired-$actual}] [get_ports drive]
    }
}
report_checks -unconstrained -path_delay max -group_path_count 1
foreach direction {rise fall} {
    set measured [get_property [get_pins $source/A] slew_max_$direction]
    if {abs($measured-[set target_$direction]) > 0.1} {error "source A $direction slew failed calibration"}
}
set fh [open /o/joint_arr_calibrated_$::env(CORNER).txt w]
foreach cell [get_cells *] {
    foreach pin [get_pins -of_objects $cell] {
        puts $fh "[get_full_name $pin] [get_property $pin arrival_max_rise] [get_property $pin arrival_min_rise] [get_property $pin slew_max_rise] [get_property $pin arrival_max_fall] [get_property $pin arrival_min_fall] [get_property $pin slew_max_fall]"
    }
}
close $fh
puts OT_NW_ACTUAL_SOURCE_BOUNDARY_CALIBRATED
