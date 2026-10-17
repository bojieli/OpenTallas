# H-NETLIST F1 2026-10-16 (PRE_CTS, fork tiles hbfd_rly_*_fc_f<N>): every clk_out<k> buffer input is taken off the clk_in
# net for CTS (the tree is built for the registers only); fcf_clock.tcl reconnects them to the clk_in root net right
# after clock_tree_synthesis, so clk_in -> clk_out<k> is one buffer per branch (as fc_pre_cts.tcl for the fc tiles).
set ot_fc_r 0
foreach inst [[ord::get_db_block] getInsts] {
  if {![string match *u_fcb_ck* [$inst getName]]} { continue }
  $inst setDoNotTouch 0
  set it [$inst findITerm A]
  if {[$it getNet] ne "NULL"} { $it disconnect }
  $inst setDoNotTouch 1
  incr ot_fc_r
}
set ot_fc_n [llength [get_ports -quiet clk_out*]]
puts "OT_FCF pre-CTS: $ot_fc_r clk_out buffer inputs taken off the clk_in net for CTS ($ot_fc_n clk_out ports)"
if {$ot_fc_r != $ot_fc_n || $ot_fc_r < 2} { error "OT_FCF: expected one clk_out buffer per clk_out port, found $ot_fc_r for $ot_fc_n" }
