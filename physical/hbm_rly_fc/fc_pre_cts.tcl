# H-NETLIST F1 2026-10-16 (PRE_CTS, spec pre_cts_extra): CTS must connect the clk_out buffer's input to its tree (the
# buffer is a sink of the clk_in clock net), so its PRE_FLOORPLAN dont_touch is lifted here; fc_clock.tcl (post-CTS
# boundary, every later step) sets it again so no repair resizes or bypasses it.  The data buffers stay dont_touch.
set ot_fc_r 0
foreach inst [[ord::get_db_block] getInsts] {
  if {[string match *u_fcb_ck* [$inst getName]]} { $inst setDoNotTouch 0; incr ot_fc_r }
}
puts "OT_FC pre-CTS: clk_out buffer dont_touch lifted ($ot_fc_r)"
if {$ot_fc_r != 1} { error "OT_FC: expected exactly one clk_out buffer, found $ot_fc_r" }
