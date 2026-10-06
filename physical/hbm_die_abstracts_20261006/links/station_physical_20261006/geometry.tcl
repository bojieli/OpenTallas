# Read only: real terminal route in /route. Called after actual export, never P&R.
read_db /route/6_final.odb
set block [ord::get_db_block]
set dbu [$block getDbUnitsPerMicron]
set fp [open /out/geometry.tsv w]
puts $fp "pin\tdirection\tsignal_type\tlayer\txmin_um\tymin_um\txmax_um\tymax_um"
foreach bt [$block getBTerms] {
 foreach bp [$bt getBPins] {
  foreach box [$bp getBoxes] {
   puts $fp [join [list [$bt getName] [$bt getIoType] [$bt getSigType] [[$box getTechLayer] getName] [expr {double([$box xMin])/$dbu}] [expr {double([$box yMin])/$dbu}] [expr {double([$box xMax])/$dbu}] [expr {double([$box yMax])/$dbu}]] "\t"]
  }
 }
}
close $fp
set die [$block getDieArea]
set area 0
foreach inst [$block getInsts] {
 set master [$inst getMaster]
 set area [expr {$area+double([$master getWidth])*[$master getHeight]/$dbu/$dbu}]
}
set fp [open /out/geometry_summary.tsv w]
puts $fp "die_width_um\t[expr {double([$die dx])/$dbu}]"
puts $fp "die_height_um\t[expr {double([$die dy])/$dbu}]"
puts $fp "instance_count\t[llength [$block getInsts]]"
puts $fp "placed_cell_area_um2\t$area"
puts $fp "net_count\t[llength [$block getNets]]"
puts $fp "port_count\t[llength [$block getBTerms]]"
puts $fp "dbu_per_um\t$dbu"
close $fp
puts ACTUAL_STATION_GEOMETRY_DONE
exit
