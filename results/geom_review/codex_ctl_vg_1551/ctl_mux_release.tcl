# Source after the original raw-bank release, before DPL.
set cm_r [open $::env(RESULTS_DIR)/ot_ctl_mux_fixed.txt r]
while {[gets $cm_r n]>=0} {
 set c [[ord::get_db_block] findInst $n]
 if {$c eq "NULL"} { error "CTL_MUX release missing $n" }
 $c setPlacementStatus PLACED
}
close $cm_r
