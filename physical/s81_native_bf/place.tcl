# Native full BF pair: four aligned-v2 ROMs, two columns, registered PP2 capture.
# Original physical/abi3/w10_wake_column_place.tcl provides the grid helpers.
set block [ord::get_db_block]
set dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set row0 [lindex [$block getRows] 0]
set origin [$row0 getOrigin]
set xgrid0 [expr {double([lindex $origin 0])/$dbu}]
set ygrid0 [expr {double([lindex $origin 1])/$dbu}]
set xpitch [expr {double([[$row0 getSite] getWidth])/$dbu}]
set ypitch [expr {double([[$row0 getSite] getHeight])/$dbu}]
proc ot_snap {v origin pitch} { return [expr {$origin+round(($v-$origin)/$pitch)*$pitch}] }
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
    if {$best eq {}} { error "No intersection of site and track origin grids" }
    return [expr {$best/1000.0}]
}
proc ot_find {block want} {
    foreach inst [$block getInsts] {
        set n [string map {\\ {}} [$inst getName]]
        # the element sits at u_elem, g_orig.u_elem (RECUT = 0) or g_rc.u_elem (RECUT q-element build)
        if {$n eq $want || $n eq "g_orig.$want" || $n eq "g_rc.$want"} { return $inst }
    }
    error "placement hook: no instance $want"
}
proc ot_row_orient {block y dbu} {
    set yi [expr {round($y*$dbu)}]
    foreach row [$block getRows] { if {[lindex [$row getOrigin] 1] == $yi} { return [$row getOrient] } }
    error "No placement row at Y=$y"
}
set core [$block getCoreArea]
set x0 [expr {double([$core xMin])/$dbu}]
set y0 [expr {double([$core yMin])/$dbu}]
set x1 [expr {double([$core xMax])/$dbu}]
set y1 [expr {double([$core yMax])/$dbu}]
set first [ot_find $block {u_elem.g_mac[0].g_pp.u_rom0}]
set master [$first getMaster]
set rw [expr {double([$master getWidth])/$dbu}]
set rh [expr {double([$master getHeight])/$dbu}]
set xl [expr {$x0+10.8}]
set xr [expr {$x1-10.8-$rw}]
set yl [expr {($y0+$y1)/2-$rh-5.4}]
set yh [expr {($y0+$y1)/2+5.4}]
if {$xr-$xl < $rw+21.6 || $yl < $y0+5.4 || $yh+$rh > $y1-5.4} {
 error "native BF four-ROM core has inadequate macro/logic clearance"
}
set specs [list {u_elem.g_mac[0].g_pp.u_rom0} $xl $yl R0 \
 {u_elem.g_mac[0].g_pp.u_rom1} $xl $yh MX \
 {u_elem.g_mac[1].g_pp.u_rom0} $xr $yl MY \
 {u_elem.g_mac[1].g_pp.u_rom1} $xr $yh R180]
foreach {name mx my orient} $specs {
 set inst [ot_find $block $name]
 # rtl_macro_placer leaves its macros LOCKED; unlock before re-placing (ODB-0360 on orientation change)
 $inst setPlacementStatus PLACED
 set px [ot_snap_joint $mx $xgrid0 $xpitch 0.0 0.048]
 set py [ot_snap_joint $my $ygrid0 $ypitch 0.0 0.048]
 place_inst -name [$inst getName] -location [format "%.3f %.3f" $px $py] -orientation $orient -status FIRM
 puts "S81_BF_ROM [$inst getName] x=$px y=$py w=$rw h=$rh orient=$orient"
}
