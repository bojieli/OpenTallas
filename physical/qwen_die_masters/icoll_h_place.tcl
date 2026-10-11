# el1011-q-coll 2026-10-11 (MACRO_PLACEMENT_TCL): qfd_io_collective hierarchical parent (pr2h, 520 x 840).  Four hardened
# lane slices (ot_coll_fold_slice, 180 x 180, routed qfd_io_collective_fs) stacked on the left, mirrored (MY) so their
# source pins face the ~100 um central channel (head / s0 registers) and their sum pins face the left die edge (out_*
# pins); the four source-FIFO macros (ot_sram_1r1w_32x546_m1) in a column on the right beside the rx pins.  Every bus:
# macro -> head regs <= ~110 um, s0 -> slice <= ~100 um, slice -> out pin <= ~25 um; red_in reaches the stack <= ~420 um.
set ot_blk [ord::get_db_block]
set sl {}; set fm {}
foreach i [$ot_blk getInsts] {
  set m [[$i getMaster] getName]
  if {$m eq "ot_coll_fold_slice"} { lappend sl [$i getName] } elseif {$m eq "ot_sram_1r1w_32x546_m1"} { lappend fm [$i getName] }
}
set sl [lsort -dictionary $sl]; set fm [lsort -dictionary $fm]
if {[llength $sl] != 4 || [llength $fm] != 4} { puts "OT_ICH ERROR: slices [llength $sl] fifo macros [llength $fm] (want 4 / 4)"; exit 1 }
foreach n $sl y {40.23 240.03 439.83 639.63} {
  place_macro -macro_name $n -location [list 25.056 $y] -orientation MY
  puts "OT_ICH slice $n at 25.056 $y MY"
}
foreach n $fm y {79.92 279.99 480.06 680.13} {
  place_macro -macro_name $n -location [list 302.184 $y] -orientation R0
  puts "OT_ICH fifo $n at 302.184 $y"
}
