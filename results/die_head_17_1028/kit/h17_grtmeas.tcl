# DIE-HEAD-17 DIAGNOSTIC (copy of h16_grtmeas + SPEF for the FF routed measurement) (POST_GLOBAL_ROUTE, kit-local, env H16_MEAS=1): routed-RC (GRT) clock arrivals at TT.
file mkdir /work/meas17g
set_propagated_clock [all_clocks]
estimate_parasitics -global_routing
estimate_parasitics -global_routing -spef_file /work/meas17g/grt.spef
puts "H17 SPEF written"
set out [open /work/meas17g/TT.meas w]
array set mean {}
set fh [open /work/core_latency.txt]; while {[gets $fh l] >= 0} { if {[string match #* $l]} continue; lassign $l i p ps; set mean($i/$p) $ps }; close $fh
foreach k [array names mean] {
  set pin [get_pins -quiet $k]
  if {$pin eq ""} continue
  puts $out "CORE $k [get_property $pin arrival_max_rise] [get_property $pin arrival_min_rise] [get_property $pin arrival_max_fall] [get_property $pin arrival_min_fall] [get_property $pin slew_max_rise] $mean($k)"
}
foreach p [all_registers -clock_pins] {
  set a [get_property $p arrival_max_rise]
  if {$a eq "" || [string match *INF* $a]} continue
  puts $out "CK [get_property $p full_name] $a [get_property $p arrival_min_rise] [get_property $p arrival_max_fall] [get_property $p arrival_min_fall] [get_property $p slew_max_rise] [get_property $p slew_max_fall]"
}
close $out
set out [open /work/meas17g/trunk.txt w]
foreach i [get_cells -quiet {h16_* h15_*}] {
  set n [get_full_name $i]; set a [get_pins -quiet $n/A]; set y [get_pins -quiet $n/Y]
  if {$a eq "" || $y eq ""} continue
  puts $out "CELL $n A [get_property $a arrival_max_rise] sA [get_property $a slew_max_rise] Y [get_property $y arrival_max_rise]"
}
close $out
report_check_types -max_slew -max_capacitance -violators > /work/meas17g/TT.checks_viol
set ::env(OT_PS_OUT) /work/meas17g/TT.ps.tsv
set ::env(CORNER) TT
source /work/pair_skew.tcl
puts "H16_GRTMEAS done"
