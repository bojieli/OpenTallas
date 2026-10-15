# PRE_IO_PLACEMENT (el1011-hbm-coll 2026-10-11, route_ps.sh INTERIOR=4): pin plan of the hierarchical hfd_coll DIE TILE.
# A die tile needs one CORE face and one LINK face (the R25GQ die puts the 9 llk ports on its W / E / S edges and the
# core in between); pins only on the left / right faces (horizontal layers M4 / M6), so a west-column tile mirrored MY
# keeps every pin on its track (MY leaves y unchanged).
#   left  (core):  rb_d* rb_v rb_cr sw_cr_ret clk rst_n stall fault  low band beside rows r0..r2 (u_rb banks r1/r2)
#                  qp_* qr_*                                         high band beside rows r3..r5 (u_qp r4, u_qr r5)
#   right (link):  ph_rx_flit* ph_rx_v   low band beside r0..r1 (u_wrx r0)
#                  ph_tx_flit* ph_tx_v   high band beside r2..r5 (u_wtx r3 -> u_txq)
set block [ord::get_db_block]
set units [$block getDbUnitsPerMicron]
set die [$block getDieArea]
set dw [expr {double([$die dx])/$units}]
set dh [expr {double([$die dy])/$units}]
set mw 94.824
set mh 41.040
set gap [expr {[info exists ::env(OT_HCOLL_GAP)] ? double($::env(OT_HCOLL_GAP)) : ($dw < 460.0 ? 20.0 : 24.0)}]
set array_h [expr {6*$mh+5*$gap}]
set y0 [expr {($dh-$array_h)/2}]
proc ot_rowy4 {r} { upvar y0 y0 mh mh gap gap; return [expr {$y0 + $r*($mh+$gap)}] }
proc ot_r4 {v} { return [format %.0f $v] }
set lo 4.0; set hi [expr {$dh - 4.0}]
set lsplit [expr {[ot_rowy4 3] - $gap/2 - $mh/2}]
set rsplit [expr {[ot_rowy4 2] - $gap/2 + $mh/2}]
set_io_pin_constraint -region left:[ot_r4 $lo]-[ot_r4 $lsplit] -pin_names {rb_d* rb_v rb_cr sw_cr_ret clk rst_n stall fault}
set_io_pin_constraint -region left:[ot_r4 $lsplit]-[ot_r4 $hi] -pin_names {qp_din* qr_din* qp_push qr_push}
set_io_pin_constraint -region right:[ot_r4 $lo]-[ot_r4 $rsplit] -pin_names {ph_rx_flit* ph_rx_v}
set_io_pin_constraint -region right:[ot_r4 $rsplit]-[ot_r4 $hi] -pin_names {ph_tx_flit* ph_tx_v}
puts "HCOLL_PINS_DF4 left core [ot_r4 $lo]-[ot_r4 $lsplit] / q [ot_r4 $lsplit]-[ot_r4 $hi]; right rx [ot_r4 $lo]-[ot_r4 $rsplit] / tx [ot_r4 $rsplit]-[ot_r4 $hi] die ${dw}x${dh}"
