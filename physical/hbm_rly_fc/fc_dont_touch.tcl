# H-NETLIST F1 2026-10-16 (PRE_FLOORPLAN): keep the forwarding buffers of hbfd_rly_*_fc exactly as written -- the clk_out
# buffer (*u_fcb_ck*) and one output buffer per o bit (*u_fcb_o*), all BUFx12f -- through floorplan remove_buffers,
# timing-driven placement unbuffering, resizing and every repair pass.  The data buffers' nets (Q -> buffer -> o port)
# are kept too, so no hold / repair cell can be inserted between the register and its matched output driver; the clock
# buffer's input net is the clk_in clock net and stays free for CTS.
set ot_fc_n 0; set ot_fc_nn 0; set ot_fc_bad {}
foreach inst [[ord::get_db_block] getInsts] {
  set nm [$inst getName]
  if {![string match *u_fcb_* $nm]} { continue }
  if {[[$inst getMaster] getName] ne "BUFx12f_ASAP7_75t_R"} { lappend ot_fc_bad "$nm=[[$inst getMaster] getName]" }
  $inst setDoNotTouch 1; incr ot_fc_n
  if {[string match *u_fcb_o* $nm]} {
    foreach it [$inst getITerms] {
      set net [$it getNet]
      if {$net ne "NULL" && ![$net isSpecial]} { $net setDoNotTouch 1; incr ot_fc_nn }
    }
  }
}
puts "OT_FC dont_touch $ot_fc_n forwarding buffers, $ot_fc_nn data nets"
if {$ot_fc_n == 0} { error "OT_FC: no forwarding buffer (*u_fcb_*) in the netlist" }
if {[llength $ot_fc_bad]} { error "OT_FC: forwarding buffers of the wrong master: [lrange $ot_fc_bad 0 4]" }
