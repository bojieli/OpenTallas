# HBM-HCBANK6 10-20 (kit-local PRE_GLOBAL_PLACE hook, hbm_hcq_tree16_c1/c1b and the hub cluster): the reviewed native-fanout
# LAT-7 adder graph (rtl/hdc/ot_hdc_fp32_add_lat7_fan32_native.v, 520dbea3a) carries (* keep, dont_touch *) on every cell
# so synthesis keeps the proven mapped graph.  In OpenROAD a dont_touch load pin makes the timing-driven global-placement /
# repair_design buffering abort (RSZ-3006 "Failed to insert buffer before loads", gate 10-20 03:40).  After synthesis the
# graph is fixed; sizing and buffering preserve its logic (buffers are transparent to the native census), so the physical
# dont_touch is cleared on the graph's instances and nets only (names containing ".u_native."); nothing else changes.
set ot_nu_b [ord::get_db_block]
set ot_nu_i 0; set ot_nu_n 0
foreach ot_nu_x [$ot_nu_b getInsts] {
  if {[string first ".u_native." [$ot_nu_x getName]] >= 0 && [$ot_nu_x isDoNotTouch]} { $ot_nu_x setDoNotTouch 0; incr ot_nu_i }
}
foreach ot_nu_x [$ot_nu_b getNets] {
  if {[string first ".u_native." [$ot_nu_x getName]] >= 0 && [$ot_nu_x isDoNotTouch]} { $ot_nu_x setDoNotTouch 0; incr ot_nu_n }
}
puts "OT_NATIVE_UNTOUCH insts=$ot_nu_i nets=$ot_nu_n"
