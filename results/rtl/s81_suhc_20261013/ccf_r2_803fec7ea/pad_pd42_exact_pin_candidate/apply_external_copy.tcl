read_db /base/4_1_cts.odb
source /diag/exact_m2_candidate.tcl
write_db /diag/corrected_pins_only.odb
set b [ord::get_db_block]
set d [$b getDieArea]
puts "ACTUAL_DIE [$d xMin] [$d yMin] [$d xMax] [$d yMax] [[ord::get_db_tech] getDbUnitsPerMicron]"
foreach t [$b getBTerms] {
foreach bp [$t getBPins] {foreach box [$bp getBoxes] {puts "ACTUAL_PIN [$t getName] [[$box getTechLayer] getName] [$box xMin] [$box yMin] [$box xMax] [$box yMax]"}}
}
exit
