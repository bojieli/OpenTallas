# Track-aligned successor (2026-10-03, results/uarch/macro_pin_access_audit_20261003): the body of
# physical/v41x_window_bank4_macro_place.tcl (left byte-identical) with every macro origin computed per orientation by
# physical/common/ot_macro_track_snap.tcl from the macro's own pins, W/H and the platform tracks, and a
# floorplan-time OT_MACRO_TRACK_ASSERT that fails the run if any macro signal pin centre is off-track.
source [file join [expr {[info exists ::env(OT_SRC_ROOT)] ? $::env(OT_SRC_ROOT) : "/src"}] physical/common/ot_macro_track_snap.tcl]
# Four one-sector window-bank macros in a 420 x 270 um representative slice.
# Keep R0 so horizontal M4 power straps meet the current PDN grid. The
# preceding R90 attempt reached macro placement but failed PDN-0233 because
# the macro power straps rotated away from the platform's macro grid.
set block [ord::get_db_block]
set dbu [$block getDbUnitsPerMicron]
set xs {35 225 35 225}
set ys {50 50 145 145}
set seen 0
foreach mem [$block getInsts] {
    if {[[$mem getMaster] getName] ne "ot_sram_1r1w_256x256_m2_r2c2"} { continue }
    if {![regexp {g_bank.*([0-3]).*u_mem} [$mem getName] ignored i]} { continue }
    # v1 set the raw (unsnapped) location: 8-16 nm off the M4 tracks (DRT-0255 x12)
    ot_mts::place $mem [lindex $xs $i] [lindex $ys $i] R0 LOCKED
    incr seen
}
if {$seen != 4} { error "expected four window bank macros, found $seen" }
ot_mts::assert_on_track -label [file tail [info script]]
