set corner $::env(OT_CLOCK_CORNER)
set base /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
foreach pattern [list "asap7sc7p5t_AO_RVT_${corner}_*.lib*" "asap7sc7p5t_OA_RVT_${corner}_*.lib*" "asap7sc7p5t_SIMPLE_RVT_${corner}_*.lib*" "asap7sc7p5t_INVBUF_RVT_${corner}_*.lib*" "asap7sc7p5t_SEQ_RVT_${corner}_*.lib*"] {
 foreach f [glob -directory $base $pattern] {read_liberty $f}
}
read_db /native/6_final.odb
read_sdc /native/6_final.sdc
read_spef /native/6_final.spef
sta::find_timing_paths -path_delay max -group_path_count 1
puts "OT_NATIVE_CLOCK_CONSTRAINTS_UNCHANGED $corner"
report_clock_properties [all_clocks]
foreach name {{fi0[0]} {fn0[0]} {fo0[0]}} {
 set p [get_ports -quiet $name]
 puts "OT_NATIVE_CLOCK_ARRIVAL $corner $name"
 puts "OT_NATIVE_CLOCK_TAGS_BEGIN $name"
 sta::report_arrival $name -digits 6
 puts "OT_NATIVE_CLOCK_TAGS_END $name"
}
foreach name {{fn0[0]} {fo0[0]}} {
 puts "OT_NATIVE_CLOCK_PATH_BEGIN $corner $name"
 report_checks -from [get_ports -quiet {fi0[0]}] -to [get_ports -quiet $name] -unconstrained -path_delay min_max -group_path_count 4 -format full_clock_expanded -fields {slew cap fanout} -digits 6
 puts "OT_NATIVE_CLOCK_PATH_END $corner $name"
}
set block [ord::get_db_block]
foreach name {{fn0[0]} {fo0[0]}} {
 set bt [$block findBTerm $name]
 set net [$bt getNet]
 set seen [dict create]
 set level 0
 while {$net ne "NULL" && $net ne ""} {
  set nm [$net getName]
  if {[dict exists $seen $nm]} {error "cycle in native clock cone $name"}
  dict set seen $nm 1
  set drivers {}
  foreach it [$net getITerms] {if {[$it getIoType] eq "OUTPUT"} {lappend drivers $it}}
  set inputs {}
  foreach b [$net getBTerms] {if {[$b getIoType] eq "INPUT"} {lappend inputs [$b getName]}}
  if {[llength $inputs]} {puts "OT_NATIVE_CLOCK_CONE_ROOT $name $level $inputs"; break}
  if {[llength $drivers] != 1} {error "native clock cone ambiguous driver $name $nm"}
  set d [lindex $drivers 0];set inst [$d getInst]
  set ins {}
  foreach it [$inst getITerms] {if {[$it getIoType] eq "INPUT"} {lappend ins $it}}
  if {[llength $ins] != 1} {error "native clock cone is not a single-input buffer/inverter $name"}
  puts "OT_NATIVE_CLOCK_CONE_STAGE $name $level [$inst getName] [[$inst getMaster] getName] $nm"
  set net [[lindex $ins 0] getNet]
  incr level
 }
}
puts "OT_NATIVE_CLOCK_CHARACTERIZATION_DONE $corner"
exit
