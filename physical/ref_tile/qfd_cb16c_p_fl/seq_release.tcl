# Release only the exact sequential landings recorded by this kit; preserve pin/hold ownership elsewhere.
set b [ord::get_db_block];set f $::env(RESULTS_DIR)/ot_coll_seq_landing.txt
if {![file exists $f]} {error {OT_COLL_LAND_RELEASE missing exact ownership record}}
set h [open $f r];set names [split [read $h] "\n"];close $h;set n 0
foreach name $names {
 if {$name eq ""} continue
 set i [$b findInst $name]
 if {$i eq "NULL" || ![[$i getMaster] isSequential]} {error "OT_COLL_LAND_RELEASE missing source sequential cell $name"}
 if {[$i getPlacementStatus] ne "FIRM"} {error "OT_COLL_LAND_RELEASE source landing lost FIRM ownership $name"}
 $i setPlacementStatus PLACED;incr n
}
puts "OT_COLL_LAND_RELEASE PASS $n source sequential landings for DPL"
