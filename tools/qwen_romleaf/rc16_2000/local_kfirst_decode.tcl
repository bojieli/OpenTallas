# Same-edge first-K predicate beside its existing control-register mass.
# The existing rc14 release hook removes this qrl reservation before DPL.
set qk16_block [ord::get_db_block]
set qk16_dbu [$qk16_block getDbUnitsPerMicron]
set qk16_members {};set qk16_scopes [dict create]
foreach inst [$qk16_block getInsts] {
 set name [string map [list "\\" ""] [$inst getName]]
 if {![regexp {^(.*u_kfirst_local)[/.]} $name -> scope]} {continue}
 set master [$inst getMaster]
 if {[$master isSequential] || [$master isBlock]} {error "A0 first-K decoder unexpectedly contains state or macro: $name"}
 lappend qk16_members $inst;dict set qk16_scopes $scope 1
}
if {[llength $qk16_members]==0 || [dict size $qk16_scopes]!=1} {error "A0 first-K decoder: expected one private combinational scope, got [dict size $qk16_scopes]"}
set x0 446.0;set x1 451.4;set y0 348.8;set y1 392.0
set capacity 0.0;set area 0.0
foreach row [$qk16_block getRows] {
 set r [$row getBBox]
 set capacity [expr {$capacity+max(0.0,min($x1,[$r xMax]/double($qk16_dbu))-max($x0,[$r xMin]/double($qk16_dbu)))*max(0.0,min($y1,[$r yMax]/double($qk16_dbu))-max($y0,[$r yMin]/double($qk16_dbu)))}]
}
foreach inst $qk16_members {set m [$inst getMaster];set area [expr {$area+double([$m getWidth])*[$m getHeight]/($qk16_dbu*$qk16_dbu)}]}
if {$capacity<=0 || $area/$capacity>0.25} {error "A0 first-K decode lacks row margin: area=$area capacity=$capacity"}
set qk16_region [odb::dbRegion_create $qk16_block qrl_kfirst_decoder]
$qk16_region setRegionType EXCLUSIVE
odb::dbBox_create $qk16_region [expr {round($x0*$qk16_dbu)}] [expr {round($y0*$qk16_dbu)}] [expr {round($x1*$qk16_dbu)}] [expr {round($y1*$qk16_dbu)}]
set qk16_group [odb::dbGroup_create $qk16_region qrl_kfirst_decoder]
foreach inst $qk16_members {$qk16_group addInst $inst}
puts "A0_LOCAL_KFIRST_DECODE_PASS cells=[llength $qk16_members] area=$area capacity=$capacity state_added=0 edges_added=0 clock_change=0"
