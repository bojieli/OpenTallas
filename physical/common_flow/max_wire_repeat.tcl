# POST_RESIZE hook (S81-CAPC slew, 2026-10-19; spec orfs_vars POST_RESIZE_TCL=physical/common_flow/max_wire_repeat.tcl):
# NO LONG SINGLE-DRIVER WIRE.  Routed CAPC a62 (s81sl_capc_p1_die_rc_order) closed timing (TT +326.31 / FF +17.43) but the
# final TT electrical report had two max-slew violators, 300.71 / 275.63 ps > 260: net2389 (pin register g_pin.wq[27] ->
# BUFx3 place2390 -> 157 um -> INVx1 _1653_ -> child u_tw rt[27]) and nd[0] (child u_rt ETM output cw_n_d[0] -> 135 um ->
# BUFx3 place2292 -> output pin register cw_n_d[0]); routed R 4.2-5.0 kOhm, C 25-27 fF.  Placement and post-GRT
# repair_design (slew margin 30 %) had passed both: the resizer's default wire limit left 677 single-driver nets of
# 120-165 um, and routed RC on such a net can exceed the placement estimate by more than the margin.  The structural fix
# is a repeated wire everywhere: after the ORFS 3_4 repair_design, repair_design again with -max_wire_length
# OT_MAX_WIRE_UM (default 80 um, ~1/5 of the 405 um registered reach), so every signal net is a short driven segment
# whatever its routed layer / detour; the gate's GATE_LONGNET check (spec max_signal_net_um) proves it after CTS.
# Clock nets are untouched (repair_design skips them; CTS runs later).  Buffers that land on a hard child are re-placed
# by the standard relocate hook (FIRM pin flops stay fixed: they are released only at PRE_DETAIL_PLACE).
# No constraint, limit or margin is changed.
set ot_mw_um 80
if {[info exists ::env(OT_MAX_WIRE_UM)] && $::env(OT_MAX_WIRE_UM) ne ""} { set ot_mw_um $::env(OT_MAX_WIRE_UM) }
estimate_parasitics -placement
set ot_mw_n0 [sta::network_leaf_instance_count]
set ot_mw_args [list -verbose -max_wire_length $ot_mw_um]
if {[info exists ::env(SLEW_MARGIN)] && $::env(SLEW_MARGIN) ne ""} { lappend ot_mw_args -slew_margin $::env(SLEW_MARGIN) }
if {[info exists ::env(CAP_MARGIN)] && $::env(CAP_MARGIN) ne ""} { lappend ot_mw_args -cap_margin $::env(CAP_MARGIN) }
repair_design {*}$ot_mw_args
puts "OT_MAXWIRE repair_design -max_wire_length $ot_mw_um um: leaf instances $ot_mw_n0 -> [sta::network_leaf_instance_count]"
source [file join [file dirname [file normalize [info script]]] post_resize_relocate.tcl]
