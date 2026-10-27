read_db /input/3_place.odb
set b [ord::get_db_block]
set u [$b getDbUnitsPerMicron]
set t [$b findBTerm clk_ctl]
foreach p [$t getBPins] {foreach bx [$p getBoxes] {puts "PRETREE_ACTUAL_CLOCK clk_ctl layer=[[$bx getTechLayer] getName] box_dbu=[$bx xMin],[$bx yMin],[$bx xMax],[$bx yMax] dbu=$u"}}
exit
