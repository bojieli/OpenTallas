# el1011-ds-vm/fe 2026-10-11: hierarchical dsfd_vm_fe v4 (1,520.064 x 473.04).  Physical spec: el1011-ds-vm.log HIER SPEC.
#  16 capture-lane hard tiles dsfd_vm_clt (80.64 x 230.04, routed M2-M6) g_cl[g].u_l abutted in one row under their f_cap
#  slices of the N face: x 0.432 + 80.64 g, y 226.80 (16.2-um N jog channel to the die pins).
#  10 landing FIFO macros ot_sram_1r1w_64x512_m1_r2c2 (171.288 x 77.784, R0) g_ll[l].u_ll.g_m.u_m (NSVC 1: l 0/1 svc,
#  2..5 collective words 0..3, 6 sel, 7 col, 8/9 hc):
#    S row y 30.24, slots x 20.304 + ~218.0 k: w3, sel, col, hc0, hc1, w1, w0 (46.7-um channels)
#    row 2 y 128.52 at slot 3: w2 (20.5 um below the tile wall)
#    E column x 1,328.4 beside the tile wall: svc a0 y 248.40, svc a1 y 346.68
set ot_blk [ord::get_db_block]
set ot_u [$ot_blk getDbUnitsPerMicron]
set ot_die [$ot_blk getDieArea]
set ot_xs {20.304 238.464 456.192 674.352 892.512 1110.24 1328.4}
array set ot_pos {}
set ot_pos(5) [list [lindex $ot_xs 0] 30.24]
set ot_pos(6) [list [lindex $ot_xs 1] 30.24]
set ot_pos(7) [list [lindex $ot_xs 2] 30.24]
set ot_pos(8) [list [lindex $ot_xs 3] 30.24]
set ot_pos(9) [list [lindex $ot_xs 4] 30.24]
set ot_pos(3) [list [lindex $ot_xs 5] 30.24]
set ot_pos(2) [list [lindex $ot_xs 6] 30.24]
set ot_pos(4) [list [lindex $ot_xs 3] 128.52]
set ot_pos(0) [list 1328.4 248.40]
set ot_pos(1) [list 1328.4 346.68]
set ot_n 0; set ot_t 0
foreach ot_i [$ot_blk getInsts] {
  set ot_nm [$ot_i getName]
  if {[regexp {g_ll\\?\[(\d+)\\?\]\.u_ll\.g_m\.u_m$} $ot_nm -> ot_l]} {
    if {![info exists ot_pos($ot_l)]} { error "place_macros_vmfe_h: no slot for landing lane $ot_l ($ot_nm)" }
    place_macro -macro_name $ot_nm -location $ot_pos($ot_l) -orientation R0
    incr ot_n
  } elseif {[regexp {g_cl\\?\[(\d+)\\?\]\.u_l$} $ot_nm -> ot_g] && [[$ot_i getMaster] isBlock]} {
    place_macro -macro_name $ot_nm -location [list [expr {0.432 + 80.64 * $ot_g}] 226.80] -orientation R0
    incr ot_t
  }
}
if {$ot_n != 10 || $ot_t != 16} { error "place_macros_vmfe_h: $ot_n landing macros / $ot_t clt tiles (expected 10 / 16)" }
foreach ot_i [$ot_blk getInsts] {
  if {![[$ot_i getMaster] isBlock]} { continue }
  if {[[$ot_i getMaster] getName] ne "ot_sram_1r1w_64x512_m1_r2c2"} { continue }
  set ot_bb [$ot_i getBBox]
  set ot_c [expr {min(([$ot_bb xMin] - [$ot_die xMin]), ([$ot_die xMax] - [$ot_bb xMax]), ([$ot_bb yMin] - [$ot_die yMin]), ([$ot_die yMax] - [$ot_bb yMax])) / double($ot_u)}]
  if {$ot_c < 20.0} { error "place_macros_vmfe_h: [$ot_i getName] only $ot_c um from a die edge (< 20 um)" }
}
