# LEP-CENTRAL: one full-width central standard-cell band, before tapcell.
set ot_cb [ord::get_db_block]
set ot_cd [[ord::get_db_tech] getDbUnitsPerMicron]
set ot_cr {}
set ot_keep 0
foreach row [$ot_cb getRows] {
  set bb [$row getBBox]
  if {[$bb yMin] < round(261.36*$ot_cd) || [$bb yMax] > round(291.6*$ot_cd)} {
    lappend ot_cr $row
  } else { incr ot_keep }
}
foreach row $ot_cr { odb::dbRow_destroy $row }
if {$ot_keep == 0} { error "LEP_CELL_BAND no rows in y261.36..291.6" }
puts "LEP_CELL_BAND kept=$ot_keep removed=[llength $ot_cr] y261.36..291.6"
