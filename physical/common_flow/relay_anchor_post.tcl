# PRE_GLOBAL_PLACE second pass (HBM-HC7-DBK 2026-10-20; spec "pin_hook_after_flops"): relay_anchor.tcl with the table
# OT_RLY_ANCHOR_POST, after io_flop_at_pins.tcl -- re-places capture copies that io_flop_at_pins fixed at their port
# (a port with two kept capture copies, e.g. a response valid landed beside the bank AND half way to the controller).
set ::ot_ra_table $::env(OT_RLY_ANCHOR_POST)
set ::ot_ra_append 1
source [file join [file dirname [file normalize [info script]]] relay_anchor.tcl]
unset ::ot_ra_table ::ot_ra_append
