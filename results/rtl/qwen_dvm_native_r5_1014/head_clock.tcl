read_db [lindex [glob /work/results/asap7/*/base/3_2_place_iop.odb] 0]
set b [ord::get_db_block]
foreach name {ck rst_n} {
 set t [$b findBTerm $name]
 foreach bp [$t getBPins] { foreach box [$bp getBoxes] {
  puts "DVM_PIN $name [[$box getTechLayer] getName] [$box xMin] [$box yMin] [$box xMax] [$box yMax] DBU [$b getDbUnitsPerMicron]"
 } }
}
exit
