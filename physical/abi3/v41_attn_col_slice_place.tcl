# POST_MACRO_PLACE hook for ot_v41_attn_col_slice (W2 attention group column).
# Nine SRAMs in one centred column: four 128x256 WINDOW banks (top), four
# 256x256 staging lanes, one 512x128 side-field macro (bottom).  Every macro
# has signal pins on both its left and right M4 edges, so the column leaves a
# standard-cell channel on both sides.  Origins are snapped to the joint
# placement-site / M4-track grid (lesson of the V4.1 microblock joint grid:
# macro Y = 0 mod 0.048 um, X legal on the site grid).
set block [ord::get_db_block]
set dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set row0 [lindex [$block getRows] 0]
set origin [$row0 getOrigin]
set xgrid0 [expr {double([lindex $origin 0])/$dbu}]
set ygrid0 [expr {double([lindex $origin 1])/$dbu}]
set xpitch [expr {double([[$row0 getSite] getWidth])/$dbu}]
set ypitch [expr {double([[$row0 getSite] getHeight])/$dbu}]
proc ot_snap_joint {value site_origin site_pitch track_origin track_pitch} {
    set so [expr {round($site_origin*1000)}]
    set sp [expr {round($site_pitch*1000)}]
    set to [expr {round($track_origin*1000)}]
    set tp [expr {round($track_pitch*1000)}]
    set center [expr {round(($value*1000-$so)/$sp)}]
    set best {}; set bestdist 1000000000
    for {set delta -2000} {$delta <= 2000} {incr delta} {
        set candidate [expr {$so+($center+$delta)*$sp}]
        if {($candidate-$to)%$tp != 0} { continue }
        set dist [expr {abs($candidate-$value*1000)}]
        if {$dist < $bestdist} { set best $candidate; set bestdist $dist }
    }
    if {$best eq {}} { error "No intersection of site and track origin grids" }
    return [expr {$best/1000.0}]
}
set banks {}; set stgs {}; set sides {}
foreach inst [$block getInsts] {
    set m [[$inst getMaster] getName]
    if {$m eq "ot_sram_1r1w_128x256_m1_r2c2"} { lappend banks [$inst getName] }
    if {$m eq "ot_sram_1r1w_256x256_m2_r2c2"} { lappend stgs [$inst getName] }
    if {$m eq "ot_sram_1r1w_512x128_m4_r2c2"} { lappend sides [$inst getName] }
}
if {[llength $banks] != 4 || [llength $stgs] != 4 || [llength $sides] != 1} {
    error "column cut expects 4+4+1 SRAMs, found [llength $banks]+[llength $stgs]+[llength $sides]"
}
set order [concat [lsort -dictionary $sides] [lsort -dictionary -decreasing $stgs] [lsort -dictionary -decreasing $banks]]
set die [$block getDieArea]
set diew [expr {double([$die xMax]-[$die xMin])/$dbu}]
set gap $::env(OT_COL_GAP_UM)
set y $::env(OT_COL_Y0_UM)
foreach n $order {
    set inst [$block findInst $n]
    set master [$inst getMaster]
    set w [expr {double([$master getWidth])/$dbu}]
    set h [expr {double([$master getHeight])/$dbu}]
    set x [ot_snap_joint [expr {($diew-$w)/2.0}] $xgrid0 $xpitch 0.0 0.048]
    set ys [ot_snap_joint $y $ygrid0 $ypitch 0.0 0.048]
    place_inst -name $n -location [format "%.3f %.3f" $x $ys] -orientation R0 -status FIRM
    puts "OT_COL_PLACE $n [$master getName] $x $ys"
    set y [expr {$ys + $h + $gap}]
}
