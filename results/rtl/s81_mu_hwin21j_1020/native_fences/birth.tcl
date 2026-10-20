read_db /out/assigned.odb
source /src/physical/ref_tile/dsdv_mu_hwin_c21j/hwin_native_fences.tcl
ot_hj_fences_install
set b [ord::get_db_block]
set old [dict create]
foreach i [$b getInsts] {dict set old [$i getName] [list [$i getLocation] [$i getPlacementStatus] [expr {[$i getGroup] eq "NULL" ? "NULL" : [[$i getGroup] getName]}]]}
proc ff_sinks {group n} {
 set result {}
 foreach i [[[ord::get_db_block] findGroup ot_hj_$group] getInsts] {
  if {![regexp {^DFF} [[$i getMaster] getName]]} {continue}
  set pin [$i findITerm D]
  if {$pin ne "NULL"} {lappend result $pin}
  if {[llength $result]==$n} {return $result}
 }
 error "fixture insufficient FF sinks $group"
}
set left [ff_sinks E0 3];set right [ff_sinks E15 2]
set master [[ord::get_db] findMaster BUFx2_ASAP7_75t_R]
proc fixture_buf {name sinks} {
 global b master
 set i [odb::dbInst_create $b $master $name]
 set net [odb::dbNet_create $b ${name}_net]
 foreach pin $sinks {$pin disconnect;$pin connect $net}
 [$i findITerm Y] connect $net
 $i setLocation 0 0
 $i setPlacementStatus PLACED
 return $i
}
set direct [fixture_buf born_direct [list [lindex $left 0]]]
set mixed [fixture_buf born_mixed [list [lindex $left 1] [lindex $right 0]]]
set far [fixture_buf born_far [list [lindex $right 1]]]
set sink [lindex $left 2]
for {set j 0} {$j<40} {incr j} {set i [fixture_buf born_chain_$j [list $sink]];set sink [$i findITerm A]}
foreach {i expected} [list $direct E0 $mixed GLOBAL $far E15 $i E0] {
 set got [ot_hj_leaf_groups $i]
 if {$got ne $expected} {error "HWIN_BIRTH_FIXTURE classifier [$i getName] got=$got expected=$expected"}
}
foreach {owner expected} {E1 E1 GLOBAL GLOBAL} {
 set target NULL
 foreach macro [$b getInsts] {
  if {![[$macro getMaster] isBlock]} {continue}
  set key [string map [list [format %c 92] "" / .] [$macro getName]]
  if {[dict get $::ot_hj_macro_owner $key] ne $owner} {continue}
  if {$owner eq "GLOBAL" && [string match *g_event_mem* $key]} {continue}
  foreach pin [$macro getITerms] {
   if {[$pin getIoType] eq "INPUT" && [$pin getSigType] ni {POWER GROUND CLOCK}} {set target $pin;break}
  }
  if {$target ne "NULL"} {break}
 }
 if {$target eq "NULL"} {error "HWIN_BIRTH_FIXTURE missing macro $owner"}
 set new [fixture_buf born_macro_$owner [list $target]]
 set got [ot_hj_leaf_groups $new]
 if {$got ne $expected} {error "HWIN_BIRTH_FIXTURE macro $owner got=$got"}
}
set births [ot_hj_assign_births 1]
set count 0;dict for {g names} $births {incr count [llength $names]}
if {$count != 45} {error "HWIN_BIRTH_FIXTURE expected45 got$count"}
dict for {name state} $old {
 set q [$b findInst $name]
 set now [list [$q getLocation] [$q getPlacementStatus] [expr {[$q getGroup] eq "NULL" ? "NULL" : [[$q getGroup] getName]}]]
 if {$now ne $state} {error "HWIN_BIRTH_FIXTURE changed old cell $name"}
}
if {[dict size [ot_hj_assign_births 1]]} {error "HWIN_BIRTH_FIXTURE repeated births"}
puts "HWIN_BIRTH_FIXTURE_PASS cells45 chain40 macroE1/retireGLOBAL singletonE0/E15 mixedGLOBAL old_cells_unchanged repeated_empty"
