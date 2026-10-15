# hgi_hc_lane (hfd_hc_eng lane slice): its one SRAM (the write FIFO) centred against the top edge, the logic below it
# between the VM-lane face (bottom) and the top-side faces (left / right).
set b [ord::get_db_block]
set dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set die [$b getDieArea]
set w [expr {double([$die xMax]) / $dbu}]
set h [expr {double([$die yMax]) / $dbu}]
set count 0
foreach i [$b getInsts] {
 if {[[$i getMaster] isBlock]} {
  # 171.288 x 77.760; x on the 0.216 site grid, y on the 1.08 row grid; 32 um corridor above for the clock / top pins
  set x [expr {round(($w - 171.288) / 2.0 / 0.216) * 0.216}]
  set y [expr {round(($h - 77.760 - 32.4) / 1.08) * 1.08}]
  place_macro -macro_name [$i getName] -location [list $x $y] -orientation R0
  incr count
 }
}
if {$count != 1} {error "hgi_hc_lane_place requires exactly one SRAM: $count"}
