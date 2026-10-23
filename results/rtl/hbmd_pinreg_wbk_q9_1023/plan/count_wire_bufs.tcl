# read-only: count resizer long-wire repair buffers (instance names wire*) on a placed odb
# usage: ODB=<3_4_place_resized.odb> openroad -no_init -exit count_wire_bufs.tcl
read_db $::env(ODB)
set n 0; set w 0; set m [dict create]
foreach i [[ord::get_db_block] getInsts] {
  if {[[$i getMaster] isBlock]} continue
  incr n
  if {[string match "wire*" [$i getName]]} { incr w; dict incr m [[$i getMaster] getName] }
}
puts [format "WIRE_BUFS %d of %d std cells (%.1f%%) masters %s" $w $n [expr {100.0*$w/max($n,1)}] $m]
