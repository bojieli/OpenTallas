# S81-COLL3 safe4 (dscoll_lane_{w,e}_s4b): keep ONLY the rows of the full-width standard-cell band y 259.2..288.0
# (checklist 6 / measured_band_fill: no std cell in a macro channel), before tapcell.
set ot_cb [ord::get_db_block]
set ot_cd [[ord::get_db_tech] getDbUnitsPerMicron]
set ot_cr {}
set ot_keep 0
foreach row [$ot_cb getRows] {
  set bb [$row getBBox]
  if {[$bb yMin] < round(259.2*$ot_cd) || [$bb yMax] > round(288.0*$ot_cd)} {
    lappend ot_cr $row
  } else { incr ot_keep }
}
foreach row $ot_cr { odb::dbRow_destroy $row }
if {$ot_keep == 0} { error "COLL_S4B_CELL_BAND no rows in y259.2..288.0" }
puts "COLL_S4B_CELL_BAND kept=$ot_keep removed=[llength $ot_cr] y259.2..288.0"
