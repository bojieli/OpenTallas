# QW-ORPHANS2 10-20 (q6, PRE_GLOBAL_PLACE before the pin flops): the generated native fp32 adder graph
# (ot_hdc_fp32_add_lat7_fan32_native.v) carries (* dont_touch *) on every cell, so the timing-driven GPL repair could not
# buffer a weak OAI311xp33 driving 25 native loads (q5/q5w: ODB-1211 + RSZ-3006 on ...u_native.n1957) and the stage died.
# r2 (q6 r1 gate: RSZ-3006 again on n1962, whose loads include dont_touch native FLOPS; and CTS cannot connect a
# dont_touch flop's CLK, ODB-0370 in q6w): release dont_touch on ALL native cells (combinational and flops), so the
# resizer may size / buffer and CTS may connect the clock. Graph function unchanged (sizing keeps the Liberty function;
# buffering only lowers fanout); replicated INV copies stay distinct cells. The gate's native census on the actual
# GRT ODB re-checks fanout <= 32 / reach.
set ot_nr_b [ord::get_db_block]
set ot_nr_n 0; set ot_nr_k 0
foreach inst [$ot_nr_b getInsts] {
  if {![$inst isDoNotTouch]} continue
  if {![string match {*u_native*} [$inst getName]]} continue
  $inst setDoNotTouch 0; incr ot_nr_n
}
puts "OT_NATIVE_SIZE_RELEASE: released $ot_nr_n native cells"
