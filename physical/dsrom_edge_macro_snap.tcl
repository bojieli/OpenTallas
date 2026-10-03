# POST_MACRO_PLACE hook for the DS-V4.1 ROM EDGE INDEX SCORER elements (2026-10-03).
# Keeps every block macro where RTLMP put it, in the orientation RTLMP chose, and snaps its origin to the
# nearest legal track-aligned, non-overlapping point (physical/common/ot_macro_track_snap.tcl), then
# asserts every macro signal pin centre is on its layer's track (OT_MACRO_TRACK_ASSERT).
source [file join [expr {[info exists ::env(OT_SRC_ROOT)] ? $::env(OT_SRC_ROOT) : "/src"}] physical/common/ot_macro_track_snap.tcl]
set dbu [ot_mts::get_dbu]
set macros {}
foreach inst [[ord::get_db_block] getInsts] {
    if {[[$inst getMaster] isBlock]} { lappend macros $inst }
}
# snap in placement order (lower-left first) so a moved macro never jumps over an unsnapped neighbour
set keyed {}
foreach inst $macros {
    set loc [$inst getLocation]
    lappend keyed [list [lindex $loc 1] [lindex $loc 0] $inst]
}
foreach k [lsort -integer -index 0 [lsort -integer -index 1 $keyed]] {
    set inst [lindex $k 2]
    set loc [$inst getLocation]
    $inst setPlacementStatus PLACED
    ot_mts::place $inst [expr {double([lindex $loc 0])/$dbu}] [expr {double([lindex $loc 1])/$dbu}] \
        [$inst getOrient] LOCKED
}
puts "OT_EDGE_MACRO_SNAP macros=[llength $macros]"
ot_mts::assert_on_track -label [file tail [info script]]
