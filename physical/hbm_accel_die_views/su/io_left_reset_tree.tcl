# Separate the face clock from the packed M4 data bank.
set ot_pins {}
foreach bterm [[ord::get_db_block] getBTerms] {
  if {[$bterm getName] ne "clk"} {lappend ot_pins [$bterm getName]}
}
set_io_pin_constraint -region left:* -pin_names $ot_pins
set die [[ord::get_db_block] getDieArea]
set dbu [[ord::get_db_block] getDbUnitsPerMicron]
set cy [expr {([$die yMin]+[$die yMax])/2.0/$dbu}]
place_pin -pin_name clk -layer M6 -location [list 0 $cy] -pin_size {0.288 0.288}
