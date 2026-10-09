# Routine read-only diagnosis of actual capture cells, rows and M1 PG rails.
read_db $::env(OT_PG_ODB)
set b [ord::get_db_block];set u [[ord::get_db_tech] getDbUnitsPerMicron]
set f [open $::env(OT_PG_DIAG) w]
set count 0;set mismatches 0
set direct 0;set max_distance 0.0
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
foreach macro [$b getInsts] {
 if {[[$macro getMaster] getName] ne "ot_rom_4096x274_m8"} {continue}
 foreach q [$macro getITerms] {
  if {![regexp {^rd_out\[([0-9]+)\]$} [[$q getMTerm] getName] -> bit] || $bit>=256} {continue}
  set sinks {}
  foreach t [[$q getNet] getITerms] {if {$t ne $q && [$t getIoType] eq "INPUT"} {lappend sinks $t}}
  if {[llength $sinks]!=1} {error "macro q must have one capture sink"}
  set d [lindex $sinks 0]
  if {[[$d getMTerm] getName] ne "D" || ![string match *DFF* [[[$d getInst] getMaster] getName]]} {error "logic before capture"}
  set qxy [$q getAvgXY];set dxy [$d getAvgXY]
  if {![lindex $qxy 0] || ![lindex $dxy 0]} {error "missing actual q/D placement"}
  set distance [expr {(abs([lindex $qxy 1]-[lindex $dxy 1])+abs([lindex $qxy 2]-[lindex $dxy 2]))/double($u)}]
  set max_distance [expr {max($max_distance,$distance)}];incr direct
 }
}
puts $f "DIRECT_CAPTURE count=$direct max_actual_q_D_manhattan_um=$max_distance"
if {$direct!=512 || $max_distance>20.0 || $count!=512 || $mismatches!=0} {error "corrected capture geometry failed"}
puts $f "SUMMARY captures=$count actual_row_orientation_mismatch=$mismatches"
close $f
puts "SUMMARY captures=$count actual_row_orientation_mismatch=$mismatches"
