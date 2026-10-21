read_db candidate.odb
set block [ord::get_db_block]
set f [open shapes.tsv w]
foreach n {VDD VSS} {
 foreach sw [[$block findNet $n] getSWires] {
  foreach s [$sw getWires] {
   if {![$s isVia]} {
    puts $f "$n [[$s getTechLayer] getName] [$s xMin] [$s yMin] [$s xMax] [$s yMax]"
   } else {
    set v [$s getBlockVia]
    if {$v eq "NULL"} {set v [$s getTechVia]}
    lassign [$s getViaXY] x y
    foreach b [$v getBoxes] {
     puts $f "$n [[$b getTechLayer] getName] [expr {$x+[$b xMin]}] [expr {$y+[$b yMin]}] [expr {$x+[$b xMax]}] [expr {$y+[$b yMax]}]"
    }
   }
  }
 }
}
close $f
