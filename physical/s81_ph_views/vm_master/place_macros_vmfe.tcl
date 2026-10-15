# el1011-ds-vm/fe 2026-10-11: dsfd_vm_fe (1,520.064 x 311.04) landing FIFO macros (10 x ot_sram_1r1w_64x512_m1_r2c2,
# 171.288 x 77.784, R0 only: pins stay on track).  Instances g_ll[l].u_ll.g_m.u_m, NSVC 1: l 0/1 svc, 2..5 collective
# words 0..3, 6 sel, 7 col, 8/9 hc.  Plan (physical spec in el1011-ds-vm.log):
#   S row  y 30.24 (30-um S pin-face channel for the m_* pin registers), 6 slots x 20.304 + 219.7 i (48-um channels):
#          w3 (pins x 32-107), sel (108-183), col (183-259), hc1 (334-410), w1 (1,439-1,488), w0 (1,390-1,439)
#   row 2  y 128.52 (20-um channel), two macros spaced apart so the capture band above loses no adjacent lanes:
#          hc0 at slot 1, w2 (pins spread over the width) at slot 4
#   E col  x 1,324.944 (23.8 um to the E edge): svc a0 at y 30.24, svc a1 at y 128.52 (pins x 1,286-1,385)
# The capture lanes (N band, under their f_cap slices) keep y >= 128.52 (y >= 226.3 above the two row-2 macros).
set ot_blk [ord::get_db_block]
set ot_u [$ot_blk getDbUnitsPerMicron]
set ot_die [$ot_blk getDieArea]
set ot_xs {20.304 239.760 459.648 679.104 898.992 1118.448}
array set ot_pos {}
set ot_pos(5) [list [lindex $ot_xs 0] 30.24]
set ot_pos(6) [list [lindex $ot_xs 1] 30.24]
set ot_pos(7) [list [lindex $ot_xs 2] 30.24]
set ot_pos(9) [list [lindex $ot_xs 3] 30.24]
set ot_pos(3) [list [lindex $ot_xs 4] 30.24]
set ot_pos(2) [list [lindex $ot_xs 5] 30.24]
set ot_pos(8) [list [lindex $ot_xs 1] 128.52]
set ot_pos(4) [list [lindex $ot_xs 4] 128.52]
set ot_pos(0) [list 1324.944 30.24]
set ot_pos(1) [list 1324.944 128.52]
set ot_n 0
foreach ot_i [$ot_blk getInsts] {
  set ot_nm [$ot_i getName]
  if {![regexp {g_ll\\?\[(\d+)\\?\]\.u_ll\.g_m\.u_m$} $ot_nm -> ot_l]} { continue }
  if {![info exists ot_pos($ot_l)]} { error "place_macros_vmfe: no slot for landing lane $ot_l ($ot_nm)" }
  place_macro -macro_name $ot_nm -location $ot_pos($ot_l) -orientation R0
  incr ot_n
}
if {$ot_n != 10} { error "place_macros_vmfe: $ot_n landing macros (expected 10)" }
foreach ot_i [$ot_blk getInsts] {
  if {![[$ot_i getMaster] isBlock]} { continue }
  set ot_bb [$ot_i getBBox]
  set ot_c [expr {min(([$ot_bb xMin] - [$ot_die xMin]), ([$ot_die xMax] - [$ot_bb xMax]), ([$ot_bb yMin] - [$ot_die yMin]), ([$ot_die yMax] - [$ot_bb yMax])) / double($ot_u)}]
  if {$ot_c < 20.0} { error "place_macros_vmfe: [$ot_i getName] only $ot_c um from a die edge (< 20 um)" }
}
