# e11c: compact track-aligned macro array under ONE hard placement blockage.
# No standard cells may occupy the microscopic gaps required by the pin lattice.
# The blockage consumes placement area; it adds no routing obstruction or PG edit.
source [file join [expr {[info exists ::env(OT_SRC_ROOT)] ? $::env(OT_SRC_ROOT) : "/src"}] physical/common/ot_macro_track_snap.tcl]
set block [ord::get_db_block]
set dbu [ot_mts::get_dbu]
set core [$block getCoreArea]
set keyed {}
foreach inst [$block getInsts] {
    if {![[$inst getMaster] isBlock]} { continue }
    set loc [$inst getLocation]
    lappend keyed [list [lindex $loc 1] [lindex $loc 0] $inst]
    $inst setPlacementStatus NONE
}
set sorted [lsort -integer -index 0 [lsort -integer -index 1 $keyed]]
if {[llength $sorted] != 64} { error "r5a_abutted: expected all 64 SRAM macros" }
set master [[lindex [lindex $sorted 0] 2] getMaster]
set w [$master getWidth]; set h [$master getHeight]
lassign [ot_mts::site_grid] sgx sw sgy sh
set rule [ot_mts::rule $master R0]
lassign [dict get $rule x] px sx
lassign [dict get $rule y] py sy
set xp [ot_mts::lcm $sw $px]; set yp [ot_mts::lcm $sh $py]
# Preserve the same legal-origin residue at every tile. Exact body abutment
# may be impossible on this lattice; the single hard blockage covers the gaps.
set dx [expr {(($w + $xp - 1) / $xp) * $xp}]
set dy [expr {(($h + $yp - 1) / $yp) * $yp}]
set halo [expr {int(round(3.0 * $dbu))}]
lassign [ot_mts::snap_origin $master R0 \
    [expr {double([$core xMin] + $halo) / $dbu}] \
    [expr {double([$core yMin] + $halo) / $dbu}]] ox oy
set x0 [expr {int(round($ox * $dbu))}]
set y0 [expr {int(round($oy * $dbu))}]
set ncol [expr {1 + ([$core xMax] - $halo - $x0 - $w) / $dx}]
if {$ncol < 1} { error "r5a_abutted: core narrower than one aligned macro" }
set nrow [expr {(64 + $ncol - 1) / $ncol}]
set xend [expr {$x0 + ($ncol - 1) * $dx + $w}]
set yend [expr {$y0 + ($nrow - 1) * $dy + $h}]
if {$x0 < [$core xMin] || $y0 < [$core yMin] ||
    $xend + $halo > [$core xMax] || $yend + $halo > [$core yMax]} {
    error "r5a_abutted: aligned macro array and halo do not fit the core"
}
set i 0
foreach k $sorted {
    set inst [lindex $k 2]
    if {[$inst getMaster] ne $master} { error "r5a_abutted: mixed macro masters" }
    set x [expr {double($x0 + ($i % $ncol) * $dx) / $dbu}]
    set y [expr {double($y0 + ($i / $ncol) * $dy) / $dbu}]
    ot_mts::place $inst $x $y R0 LOCKED
    incr i
}
# Hard by default: retain no cell-placement channels within the macro block.
set blockage [odb::dbBlockage_create $block \
    [expr {$x0 - $halo}] [expr {$y0 - $halo}] \
    [expr {$xend + $halo}] [expr {$yend + $halo}]]
puts "OT_R5A_ABUTTED_BLOCK macros=$i cols=$ncol rows=$nrow blockages=1 gap_um=[expr {double($dx-$w)/$dbu}]x[expr {double($dy-$h)/$dbu}] placement_reserved_um2=[expr {double(($xend-$x0+2*$halo)*($yend-$y0+2*$halo))/($dbu*$dbu)}]"
ot_mts::assert_on_track -label [file tail [info script]]
