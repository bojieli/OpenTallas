set b [ord::get_db_block]
set f [open $::env(RESULTS_DIR)/rlc_placed.txt r]
foreach n [split [read $f] "\n"] {
 if {$n eq ""} continue
 set i [$b findInst $n]
 if {$i ne "NULL" && $i ne ""} {$i setPlacementStatus PLACED}
}
close $f
