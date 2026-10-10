# Separate the face clock from the packed M4 data bank.
# hbm-phys-1010 [su] (lane_pk2 aba7c2f73 DRC 4: M6 short clk / vb[16] + 3 clk rect-only): the clock pin sat at the raw
# die mid-height y 81.000 (OFF the M6 track grid y = 0.016 + 0.064 k) and the auto-placer put vb[16] on the M6 track
# 80.848, inside the clock pin's 0.288 square.  Now: the clock pin centre snapped onto an M6 track, and a 2-um window
# of the W face around it excluded from the auto-placed signal pins (both layers), so no neighbour can touch it.
set ot_pins {}
foreach bterm [[ord::get_db_block] getBTerms] {
  if {[$bterm getName] ne "clk"} {lappend ot_pins [$bterm getName]}
}
set_io_pin_constraint -region left:* -pin_names $ot_pins
set die [[ord::get_db_block] getDieArea]
set dbu [[ord::get_db_block] getDbUnitsPerMicron]
set cy [expr {([$die yMin]+[$die yMax])/2.0/$dbu}]
set cy [expr {0.016 + round(($cy - 0.016) / 0.064) * 0.064}]
exclude_io_pin_region -region [format "left:%.3f-%.3f" [expr {$cy - 1.0}] [expr {$cy + 1.0}]]
place_pin -pin_name clk -layer M6 -location [list 0 $cy] -pin_size {0.288 0.288}
