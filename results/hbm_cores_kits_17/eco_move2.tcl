# HBM-CORES-KITS-17 variant A2: move the N-face ra_* control face-flop band at pin x<40 um (NW corner) 18 um E / 13 um S
# (pin_reg stays <= ~37 um, p90 rule 30 is per-design p90); root cause = plan pin bundle ra_* at NW corner vs E-face
# 1-cycle consumers (u_ring.u_ctl.out_p -> pr_cw_o, pin span ~432 um > 405).  Legalize, all else untouched.
read_db /b/3_place.preeco.odb
set blk [ord::get_db_block]
set dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set fh [open /d/eco_flops.txt r]; set n 0
foreach nm [split [string trim [read $fh]] "\n"] {
  set i [$blk findInst $nm]
  if {$i == "NULL"} { puts "MISSING $nm"; exit 2 }
  set l [$i getLocation]
  $i setPlacementStatus PLACED
  $i setLocation [expr [lindex $l 0] + int(18.0*$dbu)] [expr [lindex $l 1] - int(13.0*$dbu)]
  incr n
}
puts "MOVED $n"
detailed_placement
check_placement -verbose
write_db /b/3_place.odb
puts ECO_DONE
