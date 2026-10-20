# HWIN-CENTRAL: one full-width central standard-cell band, before tapcell.
set ot_cb [ord::get_db_block]
set ot_cd [[ord::get_db_tech] getDbUnitsPerMicron]
set ot_cr {}
set ot_keep 0
foreach row [$ot_cb getRows] {
  set bb [$row getBBox]
  if {[$bb yMin] < round(159.84*$ot_cd) || [$bb yMax] > round(206.28*$ot_cd)} {
    lappend ot_cr $row
  } else { incr ot_keep }
}
foreach row $ot_cr { odb::dbRow_destroy $row }
if {$ot_keep == 0} { error "HWIN_CELL_BAND no rows in y159.84..206.28" }
puts "HWIN_CELL_BAND kept=$ot_keep removed=[llength $ot_cr] y159.84..206.28"
