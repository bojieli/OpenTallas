# Track-aligned successor (2026-10-03, results/uarch/macro_pin_access_audit_20261003): the body of
# physical/v41x_attn_bank_post_macro_place.tcl (left byte-identical) with every macro origin computed per orientation by
# physical/common/ot_macro_track_snap.tcl from the macro's own pins, W/H and the platform tracks, and a
# floorplan-time OT_MACRO_TRACK_ASSERT that fails the run if any macro signal pin centre is off-track.
source [file join [expr {[info exists ::env(OT_SRC_ROOT)] ? $::env(OT_SRC_ROOT) : "/src"}] physical/common/ot_macro_track_snap.tcl]
# Keep the macro's data-pin edge away from the core perimeter. The generated
# ASAP7 LEF places all 256 read and 256 write pins on its local left edge.
# RTLMP otherwise puts that edge ~3 um from the core boundary, leaving no
# useful standard-cell channel for the registered interface.
set mem [[ord::get_db_block] findInst u_mem]
# v1 set the raw 44.0 um location: 16 nm off the M4 tracks (DRT-0255 x5)
ot_mts::place $mem 44.0 44.0 [$mem getOrient] LOCKED
ot_mts::assert_on_track -label [file tail [info script]]
