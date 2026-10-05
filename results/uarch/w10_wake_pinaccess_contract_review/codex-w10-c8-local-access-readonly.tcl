read_db /inputs/5_1_grt.odb
set b [ord::get_db_block]
set tech [ord::get_db_tech]
foreach v [$tech getVias] {
 set lname [[$v getBottomLayer] getName]
 set uname [[$v getTopLayer] getName]
 if {$lname eq "M4" && $uname eq "M5"} {
  puts "DIAG|VIA|[$v getName]"
  foreach box [$v getBoxes] {puts "DIAG|VIABOX|[$v getName]|[[$box getTechLayer] getName]|[$box xMin] [$box yMin] [$box xMax] [$box yMax]"}
 }
}
foreach n {VDD VSS} {
 set net [$b findNet $n]
 foreach sw [$net getSWires] {
  foreach box [$sw getWires] {
   if {[$box xMax] < 139300 || [$box xMin] > 141700 || [$box yMax] < 123000 || [$box yMin] > 132000} {continue}
   if {[$box isVia]} {set ln VIA} else {set ln [[$box getTechLayer] getName]}
   puts "DIAG|PG|$n|$ln|[$box xMin] [$box yMin] [$box xMax] [$box yMax]"
  }
 }
}
exit
