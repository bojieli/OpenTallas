# S81-COLL-GEOM: one full-width central standard-cell band, before tapcell.
set ot_cb [ord::get_db_block]
set ot_cd [[ord::get_db_tech] getDbUnitsPerMicron]
set ot_cr {}
set ot_keep 0
foreach row [$ot_cb getRows] {
  set bb [$row getBBox]
  if {[$bb yMin] < round(216.0*$ot_cd) || [$bb yMax] > round(259.2*$ot_cd)} {
    lappend ot_cr $row
  } else { incr ot_keep }
}
foreach row $ot_cr { odb::dbRow_destroy $row }
if {$ot_keep == 0} { error "COLL_CELL_BAND no rows in y216..259.2" }
puts "COLL_CELL_BAND kept=$ot_keep removed=[llength $ot_cr] y216..259.2"
