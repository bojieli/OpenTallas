# bf-arch hardened BF column (ot_v41_bf_col): the PP ROM pair stacked at the outer (west) side, 40 um in from the edge,
# MY / R180 so the address / clock face and 130 read bits face the column logic (east); the other 144 read bits face a
# 40 um capture strip on the west.  The column's interface pins are on the east face (toward the front block).
set block [ord::get_db_block]
set dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set row0 [lindex [$block getRows] 0]
set origin [$row0 getOrigin]
set xgrid0 [expr {double([lindex $origin 0])/$dbu}]
set ygrid0 [expr {double([lindex $origin 1])/$dbu}]
set xpitch [expr {double([[$row0 getSite] getWidth])/$dbu}]
set ypitch [expr {double([[$row0 getSite] getHeight])/$dbu}]
proc ot_snap_joint {value site_origin site_pitch track_origin track_pitch} {
    set so [expr {round($site_origin*1000)}]; set sp [expr {round($site_pitch*1000)}]
    set to [expr {round($track_origin*1000)}]; set tp [expr {round($track_pitch*1000)}]
    set center [expr {round(($value*1000-$so)/$sp)}]
    set best {}; set bestdist 1000000000
    for {set delta -1000} {$delta <= 1000} {incr delta} {
        set candidate [expr {$so+($center+$delta)*$sp}]
        if {($candidate-$to)%$tp != 0} { continue }
        set dist [expr {abs($candidate-$value*1000)}]
        if {$dist < $bestdist} { set best $candidate; set bestdist $dist }
    }
    return [expr {$best/1000.0}]
}
proc ot_find {block pat} {
    foreach inst [$block getInsts] { if {[string match $pat [string map {\\ {}} [$inst getName]]]} { return $inst } }
    error "place_col: no instance $pat"
}
set core [$block getCoreArea]
set x0 [expr {double([$core xMin])/$dbu}]; set y0 [expr {double([$core yMin])/$dbu}]
set y1 [expr {double([$core yMax])/$dbu}]
set r0 [ot_find $block {*g_pp.u_rom0}]; set r1 [ot_find $block {*g_pp.u_rom1}]
set master [$r0 getMaster]
set rw [expr {double([$master getWidth])/$dbu}]; set rh [expr {double([$master getHeight])/$dbu}]
set xl [expr {$x0 + [expr {[info exists ::env(BF_COL_ROM_X)] ? $::env(BF_COL_ROM_X) : 40.0}]}]
set yl [expr {($y0+$y1)/2-$rh-5.4}]; set yh [expr {($y0+$y1)/2+5.4}]
foreach {inst my orient} [list $r0 $yl MY $r1 $yh R180] {
  $inst setPlacementStatus PLACED
  set px [ot_snap_joint $xl $xgrid0 $xpitch 0.0 0.048]
  set py [ot_snap_joint $my $ygrid0 $ypitch 0.0 0.048]
  place_inst -name [$inst getName] -location [format "%.3f %.3f" $px $py] -orientation $orient -status FIRM
  puts "BF_COL_ROM [$inst getName] x=$px y=$py orient=$orient"
}
