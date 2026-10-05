read_db /input/6_final.odb
set block [ord::get_db_block]
set out [open /output/instance_census.tsv w]
puts $out "instance\tmaster\tarea_um2\tblock"
foreach inst [$block getInsts] {
 set master [$inst getMaster]
 set area [expr {[$master getWidth]*[$master getHeight]/double([$block getDbUnitsPerMicron]*[$block getDbUnitsPerMicron])}]
 puts $out "[$inst getName]\t[$master getName]\t$area\t[$master isBlock]"
}
close $out
write_abstract_lef /output/routed_element.lef
puts "READ_ONLY_ROUTED_ELEMENT_EXPORT_DONE"
