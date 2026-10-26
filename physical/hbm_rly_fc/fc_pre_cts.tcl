# H-NETLIST F1 2026-10-16 (PRE_CTS, spec pre_cts_extra).  DIE-CLOCK F1: clk_out = clk_in through ONE buffer, i.e. the
# clk_out buffer is driven by the tile clock PIN, not by a leaf of the register tree (fc1 routes: TritonCTS took the
# buffer input as a tree sink -> clk_in->clk_out 58 ps TT through CTS buffers vs a single BUFx12f; the forwarded hop
# hold then loses the CTS share).  So the buffer input is taken OFF the clk_in net for CTS (the tree is built for the
# registers only) and fc_clock.tcl -- sourced right after clock_tree_synthesis by the kit's CTS wrapper and in every
# later step -- reconnects it to the clk_in port net (the root), dont_touch again.
set ot_fc_r 0
foreach inst [[ord::get_db_block] getInsts] {
  if {![string match *u_fcb_ck* [$inst getName]]} { continue }
  $inst setDoNotTouch 0
  set it [$inst findITerm A]
  if {[$it getNet] ne "NULL"} { $it disconnect }
  $inst setDoNotTouch 1
  incr ot_fc_r
}
puts "OT_FC pre-CTS: clk_out buffer input taken off the clk_in net for CTS ($ot_fc_r)"
if {$ot_fc_r != 1} { error "OT_FC: expected exactly one clk_out buffer, found $ot_fc_r" }
