read_db /base/4_1_cts.odb
set b [ord::get_db_block]
set d [$b getDieArea]
puts "ACTUAL_DIE [$d xMin] [$d yMin] [$d xMax] [$d yMax] [[ord::get_db_tech] getDbUnitsPerMicron]"
foreach t [$b getBTerms] {
foreach bp [$t getBPins] {foreach box [$bp getBoxes] {puts "ACTUAL_PIN [$t getName] [[$box getTechLayer] getName] [$box xMin] [$box yMin] [$box xMax] [$box yMax]"}}
}

foreach lyname {M2 M4 M5} {
set ly [[ord::get_db_tech] findLayer $lyname]
puts "LAYER $lyname DIR [$ly getDirection]"
set tg [$b findTrackGrid $ly]
foreach meth {getGridX getGridY getNumGridPatternsX getNumGridPatternsY} {if {[catch {$tg $meth} r]} {puts "TRACK_ERROR $lyname $meth $r"} else {puts "TRACK $lyname $meth $r"}}
foreach axis {X Y} {set np [$tg getNumGridPatterns$axis]; for {set i 0} {$i<$np} {incr i} {if {[catch {$tg getGridPattern$axis $i} r]} {puts "TRACK_ERROR $lyname $axis $i $r";break} else {puts "TRACK_PATTERN $lyname $axis $i $r"}}}
}
exit
