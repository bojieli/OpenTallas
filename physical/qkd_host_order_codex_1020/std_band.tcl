# Structural ORDER successor: one full-width standard-cell band, all face
# registers and core registers beside the north clock. No placement exception,
# timing mask, clock change, register removal or data-path modification.
set ot_order_block [ord::get_db_block]
set ot_order_dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set ot_order_lo [expr {round(216.0 * $ot_order_dbu)}]
set ot_order_hi [expr {round(300.24 * $ot_order_dbu)}]
set ot_order_kept 0
set ot_order_removed 0
set ot_order_row_area 0
foreach ot_order_row [$ot_order_block getRows] {
  set ot_order_box [$ot_order_row getBBox]
  if {[$ot_order_box yMin] < $ot_order_lo || [$ot_order_box yMax] > $ot_order_hi} {
    odb::dbRow_destroy $ot_order_row
    incr ot_order_removed
  } else {
    incr ot_order_kept
    set ot_order_row_area [expr {$ot_order_row_area +
      ([$ot_order_box xMax]-[$ot_order_box xMin]) *
      ([$ot_order_box yMax]-[$ot_order_box yMin])}]
  }
}
if {$ot_order_kept < 300 || $ot_order_removed == 0} {
  error "ORDER_BAND: wrong floorplan or hook order: kept=$ot_order_kept removed=$ot_order_removed"
}
puts "ORDER_BAND kept=$ot_order_kept removed=$ot_order_removed area_um2=[expr {$ot_order_row_area/double($ot_order_dbu*$ot_order_dbu)}] y_um=216..300.24"
