# Routine read-only diagnosis of actual capture cells, rows and M1 PG rails.
read_db $::env(OT_PG_ODB)
set b [ord::get_db_block];set u [[ord::get_db_tech] getDbUnitsPerMicron]
set f [open $::env(OT_PG_DIAG) w]
set count 0;set mismatches 0
foreach inst [$b getInsts] {
 set n [string map [list "\\" ""] [$inst getName]]
 if {![regexp {^cap[01]\[([0-9]+)\]} $n -> bit]} {continue}
 incr count
 lassign [$inst getLocation] ix iy
 set containing {}
 foreach row [$b getRows] {
  set rb [$row getBBox]
  if {$iy==[$rb yMin] && $ix>=[$rb xMin] && $ix<[$rb xMax]} {
   lappend containing [list [$row getName] [$row getOrient] [$rb xMin] [$rb yMin] [$rb xMax] [$rb yMax]]
  }
 }
 if {[llength $containing]!=1 || [$inst getOrient] ne [lindex [lindex $containing 0] 1]} {incr mismatches}
 puts $f "CAPTURE $n orient=[$inst getOrient] xy=$ix,$iy ROW=$containing"
 if {$bit ni {0 1 2 3 4 5 6 7 130 131 132 133}} {continue}
 foreach term [$inst getITerms] {
  set pn [[$term getMTerm] getName]
  if {$pn ni {VDD VSS}} {continue}
  puts $f "PIN $n/$pn net=[[$term getNet] getName] avg=[$term getAvgXY]"
  foreach mp [[$term getMTerm] getMPins] {foreach shape [$mp getGeometry] {
   puts $f "MASTER_PG $pn [[$shape getTechLayer] getName] [$shape xMin],[$shape yMin],[$shape xMax],[$shape yMax]"
  }}
  set xy [$term getAvgXY];set px [lindex $xy 1];set py [lindex $xy 2]
  foreach net [$b getNets] {
   if {[$net getName] ni {VDD VSS}} {continue}
   foreach sw [$net getSWires] {foreach box [$sw getWires] {
    if {[$box isVia]} {continue}
    if {[[$box getTechLayer] getName] ne "M1"} {continue}
    if {$px>=[$box xMin] && $px<=[$box xMax] && abs(($py-[$box yMin])/double($u))<0.6} {
     puts $f "RAIL $n/$pn [$net getName] [$box xMin],[$box yMin],[$box xMax],[$box yMax]"
    }
   }}
  }
 }
}
puts $f "SUMMARY captures=$count actual_row_orientation_mismatch=$mismatches"
close $f
puts "SUMMARY captures=$count actual_row_orientation_mismatch=$mismatches"
