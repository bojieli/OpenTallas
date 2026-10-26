# Run read-only on the actual gate ODB, on the fleet.
read_db $::env(ESCAPE_ODB)
set b [ord::get_db_block]
set dbu [expr {double([$b getDbUnitsPerMicron])}]
set t [[ord::get_db] getTech]
set f [open $::env(ESCAPE_OUT) w]
puts $f "DBU\t$dbu"
foreach name {M3 M4 M5} {
 set l [$t findLayer $name]
 puts $f "LAYER\t$name\t[$l getDirection]\t[$l getWidth]\t[$l getSpacing]"
 set g [$b findTrackGrid $l]
 puts $f "TRACKX\t$name\t[join [$g getGridX] ,]"
 puts $f "TRACKY\t$name\t[join [$g getGridY] ,]"
}
foreach n [$b getNets] {
 if {[$n getSigType] ni {POWER GROUND}} {continue}
 foreach w [$n getSWires] {
  foreach s [$w getWires] {
   if {![$s isVia]} {
    set l [$s getTechLayer]
    if {[$l getName] ni {M3 M4 M5}} {continue}
    puts $f "METAL\t[$n getName]\t[$l getName]\t[$s xMin]\t[$s yMin]\t[$s xMax]\t[$s yMax]"
   } else {
    set lo 99;set hi 0;set vn UNKNOWN;set v NULL
    catch {set v [$s getTechVia]}
    if {$v eq "NULL" || $v eq ""} {catch {set v [$s getBlockVia]}}
    if {$v ne "NULL" && $v ne ""} {
     catch {set vn [$v getName]}
     foreach vb [$v getBoxes] {
      set vl [$vb getTechLayer]
      if {$vl eq "NULL" || $vl eq ""} {continue}
      set lv [$vl getRoutingLevel]
      if {$lv<=0} {continue}
      set lo [expr {min($lo,$lv)}];set hi [expr {max($hi,$lv)}]
     }
    }
    if {$hi==0} {set lo 0;set hi 99}
    if {$hi<3 || $lo>5} {continue}
    puts $f "VIA\t[$n getName]\t$vn\t$lo\t$hi\t[$s xMin]\t[$s yMin]\t[$s xMax]\t[$s yMax]"
   }
  }
 }
}
foreach i [$b getInsts] {
 if {![[$i getMaster] isBlock]} {continue}
 set bb [$i getBBox]
 puts $f "MACRO\t[$i getName]\t[[$i getMaster] getName]\t[$bb xMin]\t[$bb yMin]\t[$bb xMax]\t[$bb yMax]"
}
close $f
puts ESCAPE_INVENTORY_DONE
exit
