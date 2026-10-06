# PG connectivity of a floorplan-stage ORFS result (2_floorplan.odb): psm check per net
read_db $::env(ODB)
foreach n {VDD VSS} {
  if {[catch {check_power_grid -net $n} e]} { puts "OT_PG $n FAIL $e" } else { puts "OT_PG $n PASS" }
}
set blk [ord::get_db_block]
foreach n {VDD VSS} {
  set net [$blk findNet $n]
  set c [dict create]
  foreach sw [$net getSWires] { foreach w [$sw getWires] { if {[$w isVia]} continue; dict incr c [[$w getTechLayer] getName] } }
  puts "OT_PGSHAPES $n $c"
}
exit
