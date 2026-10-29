# DIE-HEAD-17: meas14.tcl (DIE-HEAD-14) on ROUTED RC: GRT parasitics from the POST_GLOBAL_ROUTE SPEF (estimate_parasitics -global_routing -spef_file), not placement RC.
# env: CORNER TT|FF, ODB, SDC, OUT (prefix), CORE_LAT
set c $::env(CORNER)
set pat [expr {$c eq "TT" ? "*RVT_TT*" : "*RVT_FF*"}]
foreach l [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/$pat] { read_liberty $l }
foreach l [glob /work/macros/*_[string tolower $c].lib] { read_liberty $l }
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_db $::env(ODB)
read_sdc $::env(SDC)
set_propagated_clock [all_clocks]
source /work/setRC_rcx.tcl
read_spef $::env(SPEF)
report_worst_slack -max ;# build the timing graph before get_property arrival (OpenSTA segfault otherwise)
array set mean {}
set fh [open $::env(CORE_LAT)]; while {[gets $fh l] >= 0} { if {[string match #* $l]} continue; lassign $l i p ps; set mean($i/$p) $ps }; close $fh
set out [open $::env(OUT).meas w]
foreach k [array names mean] {
  set pin [get_pins -quiet $k]
  if {$pin eq ""} { puts $out "CORE $k MISSING"; continue }
  puts $out "CORE $k [get_property $pin arrival_max_rise] [get_property $pin arrival_min_rise] [get_property $pin arrival_max_fall] [get_property $pin arrival_min_fall] [get_property $pin slew_max_rise] $mean($k)"
}
set n 0
foreach p [all_registers -clock_pins] {
  set a [get_property $p arrival_max_rise]
  if {$a eq "" || [string match *INF* $a]} continue
  puts $out "CK [get_property $p full_name] $a [get_property $p arrival_min_rise] [get_property $p arrival_max_fall] [get_property $p arrival_min_fall] [get_property $p slew_max_rise] [get_property $p slew_max_fall]"; incr n
}
close $out
puts "MEAS $c clock pins $n"
report_check_types -min_pulse_width -max_slew -max_capacitance -violators > $::env(OUT).checks_viol
report_check_types -min_pulse_width > $::env(OUT).mpw
set ::env(OT_PS_OUT) $::env(OUT).ps.tsv
source /work/pair_skew.tcl
