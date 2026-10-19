set audit_block [ord::get_db_block]
if {![info exists ::ot_control_copy_aliases]} {set ::ot_control_copy_aliases {}}
proc control_root {name} {
 set seen {};while {[dict exists $::ot_control_copy_aliases $name]} {
  if {$name in $seen} {error "independent alias loop$name"}
  lappend seen $name;set name [dict get $::ot_control_copy_aliases $name]
 };return $name
}
proc control_transparent {master} {expr {[string match BUF* $master] || [string match *INV* $master] || $master in {HB2xp67_ASAP7_75t_R HB4xp67_ASAP7_75t_R}}}
proc control_canon {net {alias 1} {seen {}}} {
 if {$net eq "NULL" || $net eq ""} {return OPEN}
 if {$net in $seen} {error "independent bufferloop"};lappend seen $net
 set drivers {};foreach t [$net getITerms] {if {[$t isOutputSignal]} {lappend drivers $t}}
 if {![llength $drivers]} {
  set ports {};foreach t [$net getBTerms] {if {[$t getIoType] eq "INPUT"} {lappend ports [$t getName]}}
  if {[llength $ports]!=1} {return [list UNDRIVEN [$net getName]]}
  return [list PORT [lindex $ports 0] 0]
 }
 if {[llength $drivers]!=1} {error "independent multidriver[$net getName]"}
 set t [lindex $drivers 0];set i [$t getInst];set m [[$i getMaster] getName]
 if {[control_transparent $m]} {
  set ins {};foreach x [$i getITerms] {if {[$x isInputSignal]} {lappend ins $x}}
  if {[llength $ins]!=1} {error "independent unexpectedtransparent ABI$m"}
  set r [control_canon [[lindex $ins 0] getNet] $alias $seen]
  if {[string match *INV* $m]} {lset r end [expr {1-[lindex $r end]}]}
  return $r
 }
 set name [$i getName];if {$alias} {set name [control_root $name]}
 return [list CELL $name [[$t getMTerm] getName] 0]
}
set out [open /data/control16_${::audit_label}_equations.tsv w]
foreach i [$audit_block getInsts] {
 set m [[$i getMaster] getName]
 if {[control_transparent $m]} continue
 puts $out [join [list MASTER [$i getName] $m] \t]
 foreach t [$i getITerms] {
  if {![$t isInputSignal]} continue
  puts $out [join [list INPUT [$i getName] [[$t getMTerm] getName] [control_canon [$t getNet]]] \t]
 }
}
foreach t [$audit_block getBTerms] {
 puts $out [join [list PORT [$t getName] [$t getIoType] [$t getSigType]] \t]
 if {[$t getIoType] eq "OUTPUT"} {puts $out [join [list OUTPUT [$t getName] [control_canon [$t getNet]]] \t]}
}
close $out
# Independent all-driver load count collapses BUF/INV/HB only; copied state/logic
# drivers stay distinct. Count actual output ports too. Clock loads separately.
set clockpins {};foreach p [all_registers -clock_pins] {dict set clockpins [get_full_name $p] 1}
set loads {};set openpg 0
foreach i [$audit_block getInsts] {
 set m [[$i getMaster] getName]
 foreach t [$i getITerms] {
  if {[$t getSigType] in {POWER GROUND}} {if {[$t getNet] eq "NULL"} {incr openpg};continue}
  if {![$t isInputSignal] || [control_transparent $m]} continue
  set full [$i getName]/[[$t getMTerm] getName]
  if {[dict exists $clockpins $full]} continue
  dict incr loads [control_canon [$t getNet] 0]
 }
}
foreach t [$audit_block getBTerms] {if {[$t getIoType] eq "OUTPUT"} {dict incr loads [control_canon [$t getNet] 0]}}
set out [open /data/control16_${::audit_label}_all_driver.tsv w]
set maxload 0;set over32 0;set over16 0
foreach root [dict keys $loads] {
 set count [dict get $loads $root]
 if {[lindex $root 0] eq "PORT" && [lindex $root 1] eq "ck"} continue
 set maxload [expr {max($maxload,$count)}]
 if {$count>32} {incr over32};if {$count>16} {incr over16}
 puts $out [join [list $root $count] \t]
}
close $out
puts "INDEPENDENT_ALL_DRIVER label=$::audit_label max_terminal_load=$maxload sources_over32=$over32 sources_over16=$over16 open_power_ground_pins=$openpg includes_output_ports=1 excludes_clock_pins=1 copies_remain_distinct=1"
