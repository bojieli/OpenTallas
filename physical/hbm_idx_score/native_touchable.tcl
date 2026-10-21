# HBM-IDXSQ8 2026-10-20: PRE_GLOBAL_PLACE hook (ref_tile pin_hook_before_flops) for tiles that instantiate the bounded native
# fp32 adder graph ot_hdc_fp32_add_lat7_fan32_native (rtl/hdc, every cell keep + dont_touch so synthesis keeps the census-
# qualified graph). The mapped-netlist native32 census has already run (pre-floorplan); from placement on the cells are
# ordinary logic: timing-driven GPL / repair_design must be able to buffer their nets (hidx_score_col7_a r1:
# RSZ-3006 'Load pin ...u_native.c886/B1 is dont_touch. Cannot insert a buffer'). Releases instance AND net dont_touch
# inside every u_native instance only; no other cell is touched.
set ot_nt_i 0
set ot_nt_n 0
set ot_blk [ord::get_db_block]
foreach inst [$ot_blk getInsts] {
  if {[string match {*u_native.*} [$inst getName]] && [$inst isDoNotTouch]} {
    $inst setDoNotTouch 0
    incr ot_nt_i
  }
}
foreach net [$ot_blk getNets] {
  if {[string match {*u_native.*} [$net getName]] && [$net isDoNotTouch]} {
    $net setDoNotTouch 0
    incr ot_nt_n
  }
}
puts "OT_NATIVE_TOUCHABLE released $ot_nt_i instances, $ot_nt_n nets (u_native)"
