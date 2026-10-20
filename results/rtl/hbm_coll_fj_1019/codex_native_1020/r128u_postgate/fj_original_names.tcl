read_db $::env(SYNTH_ODB)
set f [open $::env(ORIGINAL_NAMES) w]
foreach i [[ord::get_db_block] getInsts] {puts $f [$i getName]}
close $f
