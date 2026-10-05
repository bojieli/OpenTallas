# Read-only query of terminal c8 GRT checkpoint; never invokes placement or routing.
read_db /inputs/5_1_grt.odb
set b [ord::get_db_block]
set tech [ord::get_db_tech]
puts "AUDIT|DBU|[$tech getDbUnitsPerMicron]"
foreach ln {M4 M5 V4} {
 set l [$tech findLayer $ln]
 foreach method {getWidth getSpacing getArea getMinStep getSpacingRules getEolSpacingRules getCutSpacingRules} {
  if {[catch {$l $method} value]} {puts "AUDIT|MISSING|$ln|$method|$value"} else {puts "AUDIT|RULE|$ln|$method|$value"}
 }
}
foreach ln {M4 M5} {
 set grid [$b findTrackGrid [$tech findLayer $ln]]
 puts "AUDIT|TRACK|$ln|X|[lrange [$grid getGridX] 0 3]"
 puts "AUDIT|TRACK|$ln|Y|[lrange [$grid getGridY] 0 3]"
}
foreach inst [$b getInsts] {
 if {![string match *u_rom* [$inst getName]]} {continue}
 set bb [$inst getBBox]
 puts "AUDIT|MACRO|[$inst getName]|[$inst getOrient]|[$bb xMin] [$bb yMin] [$bb xMax] [$bb yMax]"
}
foreach v [$tech getVias] {
 if {[[$v getBottomLayer] getName] ne "M4" || [[$v getTopLayer] getName] ne "M5"} {continue}
 foreach box [$v getBoxes] {puts "AUDIT|VIABOX|[$v getName]|[[$box getTechLayer] getName]|[$box xMin] [$box yMin] [$box xMax] [$box yMax]"}
}
foreach n {VDD VSS} {
 foreach sw [[$b findNet $n] getSWires] {
  foreach box [$sw getWires] {
   if {[$box isVia]} {
    if {[catch {set v [$box getTechVia]; set xy [$box getViaXY]; foreach vb [$v getBoxes] {
     set ln [[$vb getTechLayer] getName]
     if {$ln ni {M4 M5 V4}} {continue}
     set x [lindex $xy 0]; set y [lindex $xy 1]
     puts "AUDIT|PG|$n|$ln|[expr {$x+[$vb xMin]}] [expr {$y+[$vb yMin]}] [expr {$x+[$vb xMax]}] [expr {$y+[$vb yMax]}]|via"
    }} err]} {puts "AUDIT|MISSING_PG_VIA|$err"}
   } else {
    set ln [[$box getTechLayer] getName]
    if {$ln ni {M4 M5}} {continue}
    puts "AUDIT|PG|$n|$ln|[$box xMin] [$box yMin] [$box xMax] [$box yMax]|wire"
   }
  }
 }
}
exit
