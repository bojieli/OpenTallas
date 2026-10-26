# E5 R5 clock trial: preserve every existing data placement, then explicit
# small equal-depth local leaves and bounded-fanout spine/rib trunk.
set b [ord::get_db_block]
foreach i [$b getInsts] {
 if {[$i getPlacementStatus] eq "PLACED"} { $i setPlacementStatus FIRM }
}
source /work/shallow_clock.tcl
source /work/base_core_density_taps.tcl
set ::ot_dtsh::blk $::dt_blk
# Density-tap generator does not connect newly created buffer PG terminals.
# Explicitly attach the existing supplies before any clock timing is measured.
foreach t $::dt_taps {
 set i [$b findInst "ot_dtap_[lindex $t 0]"]
 ::ot_dtsh::pg $i
}
ot_dtsh::setup $::dt_blk $::dt_taps $::dt_root $::dt_cell
