# CLAUDE HBM-ABSTRACTS (hub): every lane pin on the LEFT edge (the channel edge of a lane column), M4 and M6.
set ot_pins {}
foreach bterm [[ord::get_db_block] getBTerms] { lappend ot_pins [$bterm getName] }
set_io_pin_constraint -region left:* -pin_names $ot_pins
