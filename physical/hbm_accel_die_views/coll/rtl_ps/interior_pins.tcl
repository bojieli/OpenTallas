# Bus pins occupy separate faces with two existing signal layers per face.
# All intervals are outside the fixed interior macro footprint.
set_io_pin_constraint -region left:60-480 -pin_names {qp_din* qr_din* qp_push qr_push}
set_io_pin_constraint -region right:60-480 -pin_names {ph_tx_flit* rb_d* ph_tx_v rb_v stall fault ecc_ce rx_ecc_drop*}
set_io_pin_constraint -region bottom:60-420 -pin_names {ph_rx_flit* ph_rx_v}
set_io_pin_constraint -region top:60-420 -pin_names {clk rst_n sw_cr_ret rb_cr}
# hgi-1010/d4 (route 3b90d75fa: the unconstrained face clock tap ckf landed away from its face, a 726 um average sink
# wire on its tree): each face clock tap sits in the middle of its own face (design standard: clock pin mid-face) --
# ckf (RX pin flops) bottom, ckt (TX pin flops) right.  Ports absent on a top are skipped.
set ot_fc_blk [ord::get_db_block]
set ot_fc_die [$ot_fc_blk getDieArea]
set ot_fc_u [$ot_fc_blk getDbUnitsPerMicron]
set ot_fc_xm [expr {round(([$ot_fc_die xMin] + [$ot_fc_die xMax]) / 2.0 / $ot_fc_u)}]
set ot_fc_ym [expr {round(([$ot_fc_die yMin] + [$ot_fc_die yMax]) / 2.0 / $ot_fc_u)}]
if {[$ot_fc_blk findBTerm ckf] ne "NULL"} { set_io_pin_constraint -region bottom:[expr {$ot_fc_xm-4}]-[expr {$ot_fc_xm+4}] -pin_names {ckf} }
if {[$ot_fc_blk findBTerm ckt] ne "NULL"} { set_io_pin_constraint -region right:[expr {$ot_fc_ym-4}]-[expr {$ot_fc_ym+4}] -pin_names {ckt} }
