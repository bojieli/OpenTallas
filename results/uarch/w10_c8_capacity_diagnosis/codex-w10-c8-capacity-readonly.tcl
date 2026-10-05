read_db /inputs/5_1_grt.odb
set block [ord::get_db_block]
set tech [ord::get_db_tech]
puts "DIAG|DBU|[$tech getDbUnitsPerMicron]"
foreach lname {M4 M5 M6 M7} {
 set layer [$tech findLayer $lname]
 set grid [$block findTrackGrid $layer]
 puts "DIAG|LAYER|$lname|[$layer getDirection]|[$layer getWidth]|[$layer getSpacing]"
 puts "DIAG|TRACK_X|$lname|[lrange [$grid getGridX] 0 3]"
 puts "DIAG|TRACK_Y|$lname|[lrange [$grid getGridY] 0 3]"
}
foreach inst [$block getInsts] {
 if {[string match *u_rom* [$inst getName]]} {
  set box [$inst getBBox]
  puts "DIAG|MACRO|[$inst getName]|[$inst getOrient]|[$inst getLocation]|[$box xMin] [$box yMin] [$box xMax] [$box yMax]"
 }
}
exit
