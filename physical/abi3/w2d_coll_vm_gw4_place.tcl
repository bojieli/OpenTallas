# POST_MACRO_PLACE hook for ot_v41_coll_vm_gw4_neighborhood (DEPTH_GROUPS=1):
# 16 ot_sram_1r1w_512x128 macros, bank b column c. Two macro columns
# (banks 0,1 left; banks 2,3 right), eight rows each, R0, with >=50 um
# pin channels on both short (pin) edges of every macro. Every macro origin
# is snapped to the intersection of the placement-site grid and the M4
# 0.048 um track grid (the joint-grid pin-escape fix of 685a0f4c).
# Geometry is taken from env: OT_W2D_LEFT_X, OT_W2D_RIGHT_X, OT_W2D_Y0, OT_W2D_PITCH.
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
    for {set delta -1000} {$delta <= 1000} {incr delta} {
        set candidate [expr {$so+($center+$delta)*$sp}]
        if {($candidate-$to)%$tp != 0} { continue }
        set dist [expr {abs($candidate-$value*1000)}]
        if {$dist < $bestdist} { set best $candidate; set bestdist $dist }
    }
    if {$best eq {}} { error "No intersection of site and track origin grids" }
    return [expr {$best/1000.0}]
}
set lx [expr {[info exists ::env(OT_W2D_LEFT_X)] ? $::env(OT_W2D_LEFT_X) : 60.0}]
set rx [expr {[info exists ::env(OT_W2D_RIGHT_X)] ? $::env(OT_W2D_RIGHT_X) : 406.0}]
set y0 [expr {[info exists ::env(OT_W2D_Y0)] ? $::env(OT_W2D_Y0) : 60.0}]
set pitch [expr {[info exists ::env(OT_W2D_PITCH)] ? $::env(OT_W2D_PITCH) : 42.0}]
set n 0
foreach inst [$block getInsts] {
    set name [$inst getName]
    if {![string match *u_sram $name]} { continue }
    if {![regexp {g_bank\[(\d+)\].*g_group\[(\d+)\].*g_col\[(\d+)\]} $name -> b g c]} {
        error "unexpected macro name $name"
    }
    if {$g != 0} { error "hook supports DEPTH_GROUPS=1 only ($name)" }
    set x [expr {$b < 2 ? $lx : $rx}]
    set row [expr {($b % 2) * 4 + $c}]
    set y [expr {$y0 + $row * $pitch}]
    set x [ot_snap_joint $x $xgrid0 $xpitch 0.0 0.048]
    set y [ot_snap_joint $y $ygrid0 $ypitch 0.0 0.048]
    $inst setPlacementStatus PLACED
    place_inst -name $name -location [format "%.3f %.3f" $x $y] -orientation R0 -status FIRM
    puts "OT_W2D_MACRO $name bank=$b col=$c at $x $y"
    incr n
}
if {$n != 16} { error "expected 16 VM macros, placed $n" }
puts "OT_W2D_PLACE_DONE macros=$n"
