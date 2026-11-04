# PG-CORECONN-3 probe step 1: tile floorplan PDN (ORFS order: PDN_TCL; pdngen; POST_PDN_TCL inside a proc) on the
# col_h10_r0_p4__t1 2_3 tapcell ODB, then write_abstract_lef as generate_abstract does.
set P /p
read_db $P/col_h10_r0_p4__t1/run/results/asap7/dp_col_h10_r0_p4__t1/base/2_3_floorplan_tapcell.odb
source $P/pdn_pg3_odb.tcl
pdngen
proc run_post {} { source /p/pg_publish_odb.tcl }
run_post
set b [ord::get_db_block]
foreach n {VDD VSS} {
  set bt [$b findBTerm $n]; set c7 0
  foreach bp [$bt getBPins] { foreach x [$bp getBoxes] { if {[[$x getTechLayer] getName] eq "M7"} { incr c7 } } }
  puts "OT_PROBE tile bterm $n M7 pin boxes $c7"
}
write_db $P/out/2_4_floorplan_pdn_pg3.odb
write_abstract_lef -bloat_occupied_layers $P/out/tile_pg3.lef
puts "OT_PROBE abstract written"
