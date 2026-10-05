# POST_MACRO_PLACE hook for the HA4 R5a SRAM-staging element (64 x ot_sram_1r1w_512x128_m4_r2c2).
# RTLMP abuts the macros (row pitch = macro height), so the track snap of physical/dsrom_edge_macro_snap.tcl
# finds no legal non-overlapping origin (e3: ot_mts::place error at the second row).  This hook keeps
# RTLMP's ordering (bottom-up, left-to-right, i.e. its connectivity clustering) but re-places every macro
# R0 on a regular grid from the core's lower-left corner with explicit gaps, each origin track-snapped by
# physical/common/ot_macro_track_snap.tcl, then asserts every macro pin centre is on track.
source [file join [expr {[info exists ::env(OT_SRC_ROOT)] ? $::env(OT_SRC_ROOT) : "/src"}] physical/common/ot_macro_track_snap.tcl]
set block [ord::get_db_block]
set dbu [ot_mts::get_dbu]
set core [$block getCoreArea]
set cx0 [expr {double([$core xMin]) / $dbu}]; set cy0 [expr {double([$core yMin]) / $dbu}]
set cx1 [expr {double([$core xMax]) / $dbu}]; set cy1 [expr {double([$core yMax]) / $dbu}]
# e11b physical-only recipe: leave room for both 3 um macro halos and legal cells.
# Defaults matter: run_abi3_physical does not forward these environment variables.
set gx [expr {[info exists ::env(OT_R5A_GAP_X)] ? $::env(OT_R5A_GAP_X) : 30.0}]
set gy [expr {[info exists ::env(OT_R5A_GAP_Y)] ? $::env(OT_R5A_GAP_Y) : 20.0}]
set keyed {}
foreach inst [$block getInsts] {
    if {![[$inst getMaster] isBlock]} { continue }
    set loc [$inst getLocation]
    lappend keyed [list [lindex $loc 1] [lindex $loc 0] $inst]
    $inst setPlacementStatus PLACED
    $inst setLocation [$core xMin] [$core yMin]     ;# park so the snap sees no stale overlap
}
set sorted [lsort -integer -index 0 [lsort -integer -index 1 $keyed]]
set m0 [[lindex [lindex $sorted 0] 2] getMaster]
set w [expr {double([$m0 getWidth]) / $dbu}]; set h [expr {double([$m0 getHeight]) / $dbu}]
set ncol [expr {int(floor(($cx1 - $cx0 - $gx + $gx) / ($w + $gx)))}]
if {$ncol < 1} { error "r5a_macro_grid: core [expr {$cx1-$cx0}] um narrower than one macro" }
# unplace every macro first, then place in grid order
foreach k $sorted { [lindex $k 2] setPlacementStatus NONE }
set i 0
foreach k $sorted {
    set inst [lindex $k 2]
    set c [expr {$i % $ncol}]; set r [expr {$i / $ncol}]
    set x [expr {$cx0 + $gx + $c * ($w + $gx)}]
    set y [expr {$cy0 + $gy + $r * ($h + $gy)}]
    if {$y + $h > $cy1} { error "r5a_macro_grid: row $r exceeds the core height" }
    ot_mts::place $inst $x $y R0 LOCKED
    incr i
}
puts "OT_R5A_MACRO_GRID macros=$i cols=$ncol rows=[expr {($i + $ncol - 1) / $ncol}] gap=${gx}x${gy}"
ot_mts::assert_on_track -label [file tail [info script]]
