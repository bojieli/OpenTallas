# PRE_IO_PLACEMENT (el1011-hbm-coll 2026-10-11, route_ps.sh INTERIOR=3): interior_pins_df.tcl with the TX INPUTS ON THE TOP.
# Why: df-cf086a86f-a (INTERIOR=2) left 89 slew violators (from 226), 57 on the qp/qr write side: left-face pin flops ->
# macro wd_in run ACROSS the qp/qr rows (bits 0..255 in the rightmost macro, ~310 um), plus u_rb out_d / u_wtx nets in
# the right-face corridor that carried both output buses next to the qp/qr-side traffic.  Here qp_* / qr_* enter on the
# top face over the macro array (rows r5 / r4 are the top rows), so every pin-flop -> wd_in hop is vertical; clk and the
# two credit pins move to the left face; the right face carries only the two output buses.
# (original INTERIOR=2 header follows)
# PRE_IO_PLACEMENT (el1011-hbm-coll 2026-10-11, route_ps.sh INTERIOR=2): pin plan matched to interior_macros_df.tcl.
# Same faces as interior_pins.tcl (left: qp / qr in, right: ph_tx / rb_d out, bottom: ph_rx in, top: clk / control),
# but each bus is confined to the band beside the rows it serves instead of the whole 420 um face:
#   left   qp_* / qr_*          beside rows r4..r5 (u_qp, u_qr), +- one channel
#   right  rb_d* / rb_v         beside rows r1..r2 (u_rb banks)
#   right  ph_tx_flit* / ph_tx_v / stall / fault   beside row r3 (u_wtx) and up
#   bottom ph_rx_flit* / ph_rx_v under the macro array (row r0 = u_wrx sits right above)
#   top    clk rst_n sw_cr_ret rb_cr
# Row geometry recomputed exactly as interior_macros_df.tcl (OT_HCOLL_GAP, 94.824 x 41.040 macros, centred array).
set block [ord::get_db_block]
set units [$block getDbUnitsPerMicron]
set die [$block getDieArea]
set dw [expr {double([$die dx])/$units}]
set dh [expr {double([$die dy])/$units}]
set mw 94.824
set mh 41.040
# textbook audit 10-11 (class 6: 31% util at 480x540): compact outlines (< 460 um wide) use 20 um channels
set gap [expr {[info exists ::env(OT_HCOLL_GAP)] ? double($::env(OT_HCOLL_GAP)) : ($dw < 460.0 ? 20.0 : 24.0)}]
set array_w [expr {3*$mw+2*$gap}]
set array_h [expr {6*$mh+5*$gap}]
set x0 [expr {($dw-$array_w)/2}]
set y0 [expr {($dh-$array_h)/2}]
proc ot_rowy {r} { upvar y0 y0 mh mh gap gap; return [expr {$y0 + $r*($mh+$gap)}] }
proc ot_r {v} { return [format %.0f $v] }
# left: from the bottom of r4 minus a channel to the top of r5 plus a corridor (>= 240 um for 1,092 pins)
set l0 [expr {[ot_rowy 4] - $gap}]
set l1 [expr {min($dh - 12.0, [ot_rowy 5] + $mh + $gap + 24.0)}]
if {$l1 - $l0 < 240} { set l0 [expr {$l1 - 240}] }
# right: rb_d band r1..r2, ph_tx band from r3 up
set rb0 [expr {[ot_rowy 1] - $gap/2}]
set split [expr {[ot_rowy 3] - $gap/2}]
set tx1 [expr {min($dh - 12.0, [ot_rowy 4] + $mh)}]
set rb1 [expr {[ot_rowy 3] - $gap/2}]
set tx1 [expr {min($dh - 24.0, [ot_rowy 5] + $mh)}]
set rb0 [expr {[ot_rowy 1] - $gap}]
set_io_pin_constraint -region top:[ot_r [expr {max(4.0, $x0 - 24)}]]-[ot_r [expr {min($dw - 4.0, $x0 + $array_w + 24)}]] -pin_names {qp_din* qr_din* qp_push qr_push}
set_io_pin_constraint -region right:[ot_r $rb0]-[ot_r $rb1] -pin_names {rb_d* rb_v}
set_io_pin_constraint -region right:[ot_r $rb1]-[ot_r $tx1] -pin_names {ph_tx_flit* ph_tx_v stall fault}
set_io_pin_constraint -region bottom:[ot_r [expr {$x0 - 12}]]-[ot_r [expr {$x0 + $array_w + 12}]] -pin_names {ph_rx_flit* ph_rx_v}
set_io_pin_constraint -region left:[ot_r [ot_rowy 2]]-[ot_r [ot_rowy 4]] -pin_names {clk rst_n sw_cr_ret rb_cr}
puts "HCOLL_PINS_DF3 top-tx [ot_r [expr {max(4.0, $x0 - 24)}]]-[ot_r [expr {min($dw - 4.0, $x0 + $array_w + 24)}]] rb [ot_r $rb0]-[ot_r $rb1] tx [ot_r $rb1]-[ot_r $tx1] die ${dw}x${dh}"
