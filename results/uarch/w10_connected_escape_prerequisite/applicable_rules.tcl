read_db /inputs/5_1_grt.odb
set tech [ord::get_db_tech]
# OpenDB's writer serializes the loaded rules, not the reference image's LEF.
if {[catch {write_lef /outputs/actual_db.lef} err]} {puts "RULE|EXPORT_MISSING|$err"} else {puts "RULE|EXPORT_COMPLETE"}
foreach ln {M4 M5 V4} {
 set l [$tech findLayer $ln]
 foreach method {getWidth getSpacing getArea getV55SpacingWidthsAndLengths getV55SpacingTable} {
  if {[catch {$l $method} v]} {puts "RULE|MISSING|$ln|$method|$v"} else {puts "RULE|LAYER|$ln|$method|$v"}
 }
 foreach getter {getTechLayerSpacingEolRules getTechLayerCutEnclosureRules getTechLayerCutSpacingTableDefRules getTechLayerCutClassRules} {
  set i 0
  foreach r [$l $getter] {
   if {$getter eq "getTechLayerSpacingEolRules"} {
    set fields {getEolSpace getEolWidth getEolWithin getEndToEndSpace isWithinValid isEndToEndValid isExactWidthValid isExceptExactWidthValid isWrongDirSpacingValid isParallelEdgeValid isWithcutValid}
   } elseif {$getter eq "getTechLayerCutEnclosureRules"} {
    set fields {getFirstOverhang getSecondOverhang getEolWidth getEolMinLength getMinWidth getSpacing isEolOnly isCutClassValid isAbove isBelow isWidthValid getCutClass getType}
   } elseif {$getter eq "getTechLayerCutSpacingTableDefRules"} {
    set fields {getDefault isDefaultValid isSameNet isSameMetal isSameVia isLayerValid isCenterToCenterValid isCenterAndEdgeValid isPrlValid getSpacingTable}
   } else {set fields {getName getWidth getLength getNumCuts}}
   foreach field $fields {
    if {[catch {$r $field} val]} {puts "RULE|MISSING_FIELD|$ln|$getter|$i|$field|$val"} else {
     if {$field eq "getCutClass" && $val ne "NULL"} {set val [$val getName]}
     puts "RULE|FIELD|$ln|$getter|$i|$field|$val"
    }
   }
   incr i
  }
 }
}
puts "RULE|COMPLETE"
exit
