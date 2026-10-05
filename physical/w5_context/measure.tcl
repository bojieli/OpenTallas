# Diagnostic queries only, after actual corner libs/ODB/SDC/SPEF load.
# Keep every native failed path; this file introduces no timing exceptions.
set_units -time ps -capacitance fF
set_propagated_clock [all_clocks]
report_clock_properties [all_clocks]
report_clock_latency -digits 6
report_clock_skew -setup -digits 6
report_clock_skew -hold -digits 6
report_checks -path_delay min_max -format full_clock_expanded -digits 6 -fields {slew cap input net fanout} -group_count 20
report_check_types -recovery -removal -verbose -digits 6
report_check_types -max_slew -max_capacitance -max_fanout -violators -verbose -digits 6
set roms {}
foreach c [get_cells -hierarchical *] {
 if {[get_property $c ref_name] eq "ot_rom_4096x274_m8"} {lappend roms $c}
 if {[get_property $c ref_name] eq "ICGx1_ASAP7_75t_R"} {
  puts "W5_ICG [get_full_name $c]"
  foreach suffix {CLK GCLK ENA} {
   set pin [get_pins -quiet [get_full_name $c]/$suffix]
   puts "W5_GATE_PIN [get_full_name $pin]"
   if {$suffix eq "ENA"} {report_checks -to $pin -path_delay min_max -format full_clock_expanded -digits 6 -fields {slew cap input net fanout}}
  }
 }
}
if {[llength $roms]!=4} {error "missing fullshape macros"}
report_checks -from $roms -path_delay min_max -format full_clock_expanded -digits 6 -fields {slew cap input net fanout} -group_count 20
# Net driver facts expose independent mapped Q cells, including every mutable
# AO state family. Distinct-net/cell count is reported, never inferred from RTL.
set b [ord::get_db_block]
foreach net [$b getNets] {
 set n [$net getName]
 if {![regexp {^u_stage\.u_ao\.(u_p|g_checked\.u_r)\.|^u_ld\.(u_p|g_protected\.u_r)\.|^u_(settings|go_source)\.(primary|inverse)} $n]} {continue}
 foreach p [$net getITerms] {
  if {[$p getIoType] ne "OUTPUT"} {continue}
  set i [$p getInst];set master [[$i getMaster] getName]
  if {![string match DFF* $master]} {continue}
  puts "W5_STATE_Q $n [$i getName]/[[$p getMTerm] getName] $master"
 }
}
