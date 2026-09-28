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
    $mem setPlacementStatus PLACED
    $mem setOrient R0
    $mem setLocation [expr {round([lindex $xs $i] * $dbu)}] [expr {round([lindex $ys $i] * $dbu)}]
    $mem setPlacementStatus LOCKED
    incr seen
}
if {$seen != 4} { error "expected four window bank macros, found $seen" }
