read_db /work/failed.odb
set b [ord::get_db_block]
set u [$b getDbUnitsPerMicron]
puts "A0_DB insts=[llength [$b getInsts]] nets=[llength [$b getNets]] rows=[llength [$b getRows]] groups=[llength [$b getGroups]]"
foreach name {wire61402 wire61936 wire61938 wire61949 wire61971 wire62023 wire62348 wire62361} {
 set i [$b findInst $name]
 if {$i eq "NULL"} {puts "A0_MISSING $name";continue}
 set r [$i getBBox];set g [$i getGroup];set gn NONE
 if {$g ne "NULL"} {set gn [$g getName]}
 set x0 [$r xMin];set y0 [$r yMin];set x1 [$r xMax];set y1 [$r yMax]
 set contains 0;set intersect 0
 foreach row [$b getRows] {
  set rr [$row getBBox]
  if {[$rr xMin]<=$x0 && [$rr yMin]<=$y0 && [$rr xMax]>=$x1 && [$rr yMax]>=$y1} {incr contains}
  if {[$rr xMin]<$x1 && [$rr yMin]<$y1 && [$rr xMax]>$x0 && [$rr yMax]>$y0} {incr intersect}
 }
 puts "A0_INST $name master=[[$i getMaster] getName] bbox=[list $x0 $y0 $x1 $y1] group=$gn status=[$i getPlacementStatus] containing_rows=$contains intersect_rows=$intersect dbu=$u"
}
set removed 0
foreach group [$b getGroups] {
 if {![string match qrl_* [$group getName]]} {continue}
 set region [$group getRegion]
 puts "A0_RELEASE [$group getName] members=[llength [$group getInsts]]"
 odb::dbGroup_destroy $group
 if {$region ne "NULL"} {odb::dbRegion_destroy $region}
 incr removed
}
puts "A0_RELEASED groups=$removed insts=[llength [$b getInsts]] nets=[llength [$b getNets]] rows=[llength [$b getRows]]"
detailed_placement
check_placement -verbose
write_db /work/repaired.odb
puts A0_GROUP_RELEASE_REPLAY_PASS
