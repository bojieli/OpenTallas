# el1011-q-coll 2026-10-11 (MACRO_PLACEMENT_TCL): qfd_io_collective MEMM floorplan (450 x 450).  The four per-source
# receive-FIFO macros (ot_sram_1r1w_32x546_m1) form one column beside the right face, where the 3 x 546 rx pins enter,
# with >= 22 um channels between macros and ~40 um to the die edge; the fold / adder logic owns the left ~230 um.
# Located by MASTER name, assigned bottom-to-top in instance-name order (g_r[0..3]).
set ot_blk [ord::get_db_block]
set ot_ys {21.816 125.064 228.312 331.560}
set ot_x 231.984
set ot_m {}
foreach i [$ot_blk getInsts] { if {[[$i getMaster] getName] eq "ot_sram_1r1w_32x546_m1"} { lappend ot_m [$i getName] } }
set ot_m [lsort $ot_m]
if {[llength $ot_m] != 4} { puts "OT_ICM ERROR: found [llength $ot_m] of 4 source FIFO macros"; exit 1 }
foreach n $ot_m y $ot_ys {
  place_macro -macro_name $n -location [list $ot_x $y] -orientation R0
  puts "OT_ICM placed $n at $ot_x $y"
}
