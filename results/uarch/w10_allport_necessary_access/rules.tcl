read_db /inputs/5_1_grt.odb
set tech [ord::get_db_tech]
foreach ln {M4 M5 V4} {
 set l [$tech findLayer $ln]
 foreach getter {getV54SpacingRules getTechLayerSpacingEolRules getTechLayerCutEnclosureRules getTechLayerCutSpacingTableDefRules} {
  set i 0
  foreach rule [$l $getter] {
   foreach m {getSpacing getEolWidth getEolWithin getEndOfLineWidth getWithin getParallelSpace getParallelWithin getOverhang1 getOverhang2 getMinWidth getCutClass getEolSpacing} {
    if {[catch {$rule $m} val]} {puts "FIELDS|MISSING|$ln|$getter|$i|$m|[lindex [split $val .] 0]"} else {puts "FIELDS|VALUE|$ln|$getter|$i|$m|$val"}
   }
   incr i
  }
 }
}
exit
