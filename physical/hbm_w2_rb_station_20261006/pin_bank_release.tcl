# POST_DETAIL_PLACE: return the already legalized own-pin seats to PLACED.
set blk [ord::get_db_block]
set fp [open $::env(RESULTS_DIR)/ot_out_flop_at_pins.txt r]
set count 0
while {[gets $fp name]>=0} {
 set inst [$blk findInst $name]
 if {$inst eq "NULL"} {error "W2 pin seat disappeared: $name"}
 $inst setPlacementStatus PLACED
 incr count
}
close $fp
puts "W2_PIN_BANK released $count legal seats after DPL"
