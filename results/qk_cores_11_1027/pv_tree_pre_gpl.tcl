# QK-CORES-11: face_flops (pass-1 reserve + island ft + face regs), then the plan in-core clock tree (FIRM nodes).
# The pass-1 reserve holds the entry island and the superseded [2,1] slice islands (95.04/285.12, 95.04) as hard
# blockages; DPL treats FIRM cells on blocked sites as not-in-rows (DPL-0033), so (pv_join pass-2 precedent) the entry
# reservation is consumed, the tree nodes are placed, and the entry island is re-reserved carved around them.
source /work/face_flops.tcl
set qk_b [ord::get_db_block]
set qk_n 0
foreach k [$qk_b getBlockages] {
  set r [$k getBBox]
  foreach {x0 y0 x1 y1} {185760 90720 194400 99360 90720 90720 99360 99360 280800 90720 289440 99360} {
    if {[$r xMin] >= $x0 && [$r xMax] <= $x1 && [$r yMin] >= $y0 && [$r yMax] <= $y1} { odb::dbBlockage_destroy $k; incr qk_n; break }
  }
}
puts "PV_TREE_PASS1_RESERVE_CONSUMED $qk_n"
source /work/master_core_infra.tcl
kvr2_blk $qk_b 185760 90720 194400 99360
puts "PV_TREE_INSTALLED 4 branch + 4 island nodes"
