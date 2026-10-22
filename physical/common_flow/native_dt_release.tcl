# Native-cell dont_touch release before global placement (STW-S81c-HEAD-TILE 2026-10-22).
# Why: s81hd_tile r6m / r6km / r6kf (gates 10-22 02:30-03:15) all crashed in 3_3_place_gp timing-driven repair with
# [ERROR RSZ-3006] Failed to insert buffer before loads for net ...g_native7.u_native.n3480 (ODB-1211: load pin
# ...u_native.c2804/D is dont_touch).  The bounded native fp32 adder netlist (rtl/hdc/ot_hdc_fp32_add_lat7_fan32_native*.v)
# marks every cell (* keep, dont_touch *) so SYNTHESIS keeps the census-proven graph; on a 790k-cell tile GPL stretches
# some of its internal nets and the resizer must buffer them.  The native census already ran on the mapped netlist
# (pre-floorplan); a buffer before a load or a cell resize keeps every Boolean function and only lowers loads per driver.
# This clears the ODB dont_touch flag on instances (and their nets) whose name matches OT_NDT_GLOB (default *u_native.*),
# nothing else.  Source it via spec pin_hook_before_flops (runs in PRE_GLOBAL_PLACE before io_flop_at_pins).
set ot_ndt_blk [ord::get_db_block]
set ot_ndt_glob [expr {[info exists ::env(OT_NDT_GLOB)] && $::env(OT_NDT_GLOB) ne "" ? $::env(OT_NDT_GLOB) : "*u_native.*"}]
set ot_ndt_ni 0; set ot_ndt_nn 0
foreach ot_ndt_i [$ot_ndt_blk getInsts] {
  if {![$ot_ndt_i isDoNotTouch]} continue
  if {![string match $ot_ndt_glob [string map {\\ {}} [$ot_ndt_i getName]]]} continue
  $ot_ndt_i setDoNotTouch 0; incr ot_ndt_ni
  foreach ot_ndt_it [$ot_ndt_i getITerms] {
    set ot_ndt_n [$ot_ndt_it getNet]
    if {$ot_ndt_n ne "NULL" && $ot_ndt_n ne "" && [$ot_ndt_n isDoNotTouch] && [$ot_ndt_n getSigType] ne "CLOCK"} { $ot_ndt_n setDoNotTouch 0; incr ot_ndt_nn }
  }
}
puts "NATIVE_DT_RELEASE: cleared dont_touch on $ot_ndt_ni instances / $ot_ndt_nn nets matching $ot_ndt_glob"
