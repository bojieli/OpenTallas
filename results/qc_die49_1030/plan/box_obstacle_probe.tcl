read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_db /k/run/results/asap7/dp_slw_stm_v1__cle34a73c3/base/3_2_place_iop.odb
set blk [ord::get_db_block]
set ax 445000; set ay 815000; set bx 475000; set by 836136
foreach j [$blk getInsts] { set b [$j getBBox]; if {[$b xMax]>$ax && [$b xMin]<$bx && [$b yMax]>$ay && [$b yMin]<$by && [$j getPlacementStatus] in {FIRM LOCKED FIXED COVER}} { puts "FIX [$j getName] [[$j getMaster] getName] [$j getPlacementStatus] [$b xMin] [$b yMin] [$b xMax] [$b yMax]" } }
foreach o [$blk getObstructions] { set b [$o getBBox]; if {[$b xMax]>$ax && [$b xMin]<$bx && [$b yMax]>$ay && [$b yMin]<$by} { puts "OBS [[$b getTechLayer] getName] [$b xMin] [$b yMin] [$b xMax] [$b yMax]" } }
foreach o [$blk getBlockages] { set b [$o getBBox]; if {[$b xMax]>$ax && [$b xMin]<$bx && [$b yMax]>$ay && [$b yMin]<$by} { puts "PBLK [$b xMin] [$b yMin] [$b xMax] [$b yMax]" } }
puts DONE
