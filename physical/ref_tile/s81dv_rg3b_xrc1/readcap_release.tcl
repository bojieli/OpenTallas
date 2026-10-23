# Release only our capture flops for ordinary DPL legalization.
set block [ord::get_db_block]
set f [open $::env(RESULTS_DIR)/xrc_capture_placed.txt r]
foreach n [split [read $f] "\n"] {
    if {$n eq ""} continue
    set i [$block findInst $n]
    if {$i ne "NULL" && $i ne ""} { $i setPlacementStatus PLACED }
}
close $f
