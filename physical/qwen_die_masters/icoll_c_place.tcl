# el1011-q-coll 2026-10-11: qfd_io_collective compact cluster (pr2c) macro placement; see cfg/qfd_io_collective_pr2c.env.
set ot_blk [ord::get_db_block]
set sl {}; set fm {}
foreach i [$ot_blk getInsts] {
  set m [[$i getMaster] getName]
  if {$m eq "ot_coll_fold_slice"} { lappend sl [$i getName] } elseif {$m eq "ot_sram_1r1w_32x546_m1"} { lappend fm [$i getName] }
}
set sl [lsort -dictionary $sl]; set fm [lsort -dictionary $fm]
if {[llength $sl] != 4 || [llength $fm] != 4} { puts "OT_ICH ERROR: slices [llength $sl] fifo macros [llength $fm] (want 4 / 4)"; exit 1 }
# 2 x 2 slices around the central glue channel; snapped to the all-layer track grid (macro_grid_lint: every hard-child pin on a parent track) (left column at the pr2h MY x)
foreach n $sl xy {{25.080 24.000} {25.080 228.096} {325.056 24.000} {325.056 228.096}} o {MY MY R0 R0} {
  place_macro -macro_name $n -location $xy -orientation $o
  puts "OT_ICC slice $n at $xy $o"
}
foreach n $fm xy {{75.006 432.288} {276.804 432.288} {75.006 537.312} {276.804 537.312}} {
  place_macro -macro_name $n -location $xy -orientation R0
  puts "OT_ICC fifo $n at $xy"
}
