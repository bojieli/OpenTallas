read_db /out/parent/2_3_floorplan_tapcell.odb
set block [ord::get_db_block]
set out [open /out/parent_geometry.tsv w]
set die [$block getDieArea]
puts $out "DIE\t[$die xMin]\t[$die yMin]\t[$die xMax]\t[$die yMax]"
puts $out "UNITS\t[$block getDbUnitsPerMicron]"
foreach inst [$block getInsts] {
 set master [$inst getMaster]
 if {[$master getType] ne "BLOCK"} {continue}
 set rect [$inst getBBox]
 puts $out "[$inst getName]\t[$master getName]\t[$rect xMin]\t[$rect yMin]\t[$rect xMax]\t[$rect yMax]"
}
close $out
exit
