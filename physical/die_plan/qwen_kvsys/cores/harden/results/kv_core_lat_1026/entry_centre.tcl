# KV-CORE-LAT-HEAD what-if ONLY (METHODOLOGY 12.8a emulation): the core clock pin sits at a clock island at the core's
# geometric centre (M9->M5 stack in the real plan).  Moves the clock BTerm's pin box to the core-area centre on M5;
# no lane/group taps: TritonCTS builds ONE symmetric H-tree from the centre to equal-load leaf clusters.
uplevel #0 {
set ec_blk [ord::get_db_block]
set ec_src [get_full_name [lindex [get_property [get_clocks clk] sources] 0]]
set ec_bt [$ec_blk findBTerm $ec_src]
set ca [$ec_blk getCoreArea]
set cx [expr {([$ca xMin]+[$ca xMax])/2}]; set cy [expr {([$ca yMin]+[$ca yMax])/2}]
set ly [[ord::get_db_tech] findLayer M5]
foreach bp [$ec_bt getBPins] { odb::dbBPin_destroy $bp }
set bp [odb::dbBPin_create $ec_bt]
odb::dbBox_create $bp $ly [expr {$cx-50}] [expr {$cy-50}] [expr {$cx+50}] [expr {$cy+50}]
$bp setPlacementStatus FIRM
puts [format "EC clock entry %s moved to core centre %.2f %.2f" $ec_src [expr {$cx/1000.0}] [expr {$cy/1000.0}]]
}
