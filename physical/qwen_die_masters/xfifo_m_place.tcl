# el1011-q-coll 2026-10-11 (MACRO_PLACEMENT_TCL): qfd_coll_xfifo MEMM floorplan.  The two dual-clock FIFO body macros sit
# centred with >= 25 um channels: cq (ot_sram_1r1w2c_64x516_m1, ck write / ckd read) low beside the cq pin band, sq
# (ot_sram_1r1w2c_16x546_m1, ckd write / ck read) high beside the sq pin band; the ~47 um side channels carry each
# macro's edge pins to the pin stations / capture flops.  Located by MASTER name (no flattened-path dependence).
# OT_XFM_* env overrides (um, lower-left) let a variant move them without a new script.
set ot_blk [ord::get_db_block]
set ot_loc [dict create \
  ot_sram_1r1w2c_128x516_m1 [list [expr {[info exists ::env(OT_XFM_CQ_X)] ? $::env(OT_XFM_CQ_X) : 50.112}] [expr {[info exists ::env(OT_XFM_CQ_Y)] ? $::env(OT_XFM_CQ_Y) : 25.056}]] \
  ot_sram_1r1w2c_64x516_m1 [list [expr {[info exists ::env(OT_XFM_CQ_X)] ? $::env(OT_XFM_CQ_X) : 50.112}] [expr {[info exists ::env(OT_XFM_CQ_Y)] ? $::env(OT_XFM_CQ_Y) : 25.056}]] \
  ot_sram_1r1w2c_16x546_m1 [list [expr {[info exists ::env(OT_XFM_SQ_X)] ? $::env(OT_XFM_SQ_X) : 46.656}] [expr {[info exists ::env(OT_XFM_SQ_Y)] ? $::env(OT_XFM_SQ_Y) : 131.760}]]]
set ot_n 0
foreach i [$ot_blk getInsts] {
  set m [[$i getMaster] getName]
  if {[dict exists $ot_loc $m]} {
    lassign [dict get $ot_loc $m] x y
    place_macro -macro_name [$i getName] -location [list $x $y] -orientation R0
    puts "OT_XFM placed [$i getName] ($m) at $x $y"
    incr ot_n
  }
}
if {$ot_n != 2} { puts "OT_XFM ERROR: placed $ot_n of 2 FIFO body macros"; exit 1 }
