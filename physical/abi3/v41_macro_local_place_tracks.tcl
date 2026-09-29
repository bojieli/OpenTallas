# POST_MACRO_PLACE hook for a one-SRAM VM or MP1 ME local physical cut.
# It fixes only the producer/first-capture registers beside the selected
# macro's real M4 pin sides. R0 and MX preserve the left/right assignment.
set block [ord::get_db_block]
set dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set macro {}
foreach inst [$block getInsts] {
    if {[string match *u_sram [$inst getName]]} { lappend macro $inst }
}
if {[llength $macro] != 1} { error "local cut requires one u_sram, found [llength $macro]" }
set macro [lindex $macro 0]
set initial_box [$macro getBBox]
set kind [expr {double([$initial_box xMax]-[$initial_box xMin])/$dbu > 130.0 ? "vm" : "me"}]
set row0 [lindex [$block getRows] 0]
set origin [$row0 getOrigin]
set xgrid0 [expr {double([lindex $origin 0])/$dbu}]
set ygrid0 [expr {double([lindex $origin 1])/$dbu}]
set xpitch [expr {double([[$row0 getSite] getWidth])/$dbu}]
set ypitch [expr {double([[$row0 getSite] getHeight])/$dbu}]
proc ot_snap {v origin pitch} {
    return [expr {$origin+round(($v-$origin)/$pitch)*$pitch}]
}
# The automatic one-macro placer put the macro at x=15 µm, leaving no
# left-pin escape. Fix the one macro centrally before any standard cells.
$macro setPlacementStatus PLACED
# SRAM signal pins must align to routing tracks, not standard-cell rows.
# For these two source-pinned LEFs all M4 pin centers are 0.012 mod 0.048.
# M4 horizontal tracks are also 0.012 mod 0.048. Thus macro Y must be
# 0 mod 0.048. Keep standard-cell snapping below unchanged.
# Intersect the routing-track and placement-site grids. DPL also requires
# the macro origin legal on placement rows/sites, even for a hard macro.
# Work in integer nanometres to avoid modulo phase errors.
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
set macro_x [ot_snap_joint 60 $xgrid0 $xpitch 0.0 0.048]
set macro_y [ot_snap_joint 60 $ygrid0 $ypitch 0.0 0.048]
place_inst -name [$macro getName] -location [format "%.3f %.3f" $macro_x $macro_y] -orientation R0 -status FIRM
set box [$macro getBBox]
set mx [expr {double([$box xMin])/$dbu}]
set my [expr {double([$box yMin])/$dbu}]
set mw [expr {double([$box xMax]-[$box xMin])/$dbu}]
set left {}
set right {}
foreach inst [$block getInsts] {
    set n [$inst getName]
    set master [$inst getMaster]
    if {![string match *DFF* [$master getName]]} { continue }
    set side {}
    if {$kind eq "vm"} {
        if {[string match *wr_local_mask_q* $n]} {
            set side right
        } elseif {[string match *wr_local_data_q* $n] && [regexp {([0-9]+)} $n -> bit]} {
            set side [expr {$bit < 70 ? "left" : "right"}]
        } elseif {[regexp {(rd_capture|rd_v_q|rd_group_q|rd_row_q|wr_local_en_q|wr_local_row_q|wr_v_q|wr_group_q|wr_row_q)} $n]} {
            set side left
        } elseif {[string match *wr_mask_q* $n]} {
            set side right
        } elseif {[string match *wr_data_q* $n] && [regexp {([0-9]+)} $n -> bit]} {
            set side [expr {$bit < 70 ? "left" : "right"}]
        }
    } else {
        if {[string match *wm_q* $n]} {
            set side right
        } elseif {[regexp {(q_local_r|pre_v_r|pre_e_r|pre_d_r|rq_v_r|rq_q_r|rq_plg_r|hit_q|wa_q|wd_q)} $n]} {
            set side left
        }
    }
    if {$side eq "left"} { lappend left $n }
    if {$side eq "right"} { lappend right $n }
}
set left [lsort -dictionary $left]
set right [lsort -dictionary $right]
set ncol_left [expr {$kind eq "vm" ? 16 : 22}]
set ncol_right [expr {$kind eq "vm" ? 14 : 18}]
set x_pitch 1.296
set y_pitch 0.540
set ybase [expr {$my+2.0}]
set placed 0
foreach n $left {
    set col [expr {$placed % $ncol_left}]
    set row [expr {$placed / $ncol_left}]
    set x [expr {$mx - 1.5 - ($col+1)*$x_pitch}]
    set y [expr {$ybase+$row*$y_pitch}]
    set x [ot_snap $x $xgrid0 $xpitch]
    set y [ot_snap $y $ygrid0 $ypitch]
    place_inst -name $n -location [format "%.3f %.3f" $x $y] -status FIRM
    incr placed
}
set placed 0
foreach n $right {
    set col [expr {$placed % $ncol_right}]
    set row [expr {$placed / $ncol_right}]
    set x [expr {$mx+$mw+1.5+$col*$x_pitch}]
    set y [expr {$ybase+$row*$y_pitch}]
    set x [ot_snap $x $xgrid0 $xpitch]
    set y [ot_snap $y $ygrid0 $ypitch]
    place_inst -name $n -location [format "%.3f %.3f" $x $y] -status FIRM
    incr placed
}
puts "OT_LOCAL_PLACE kind=$kind macro=[$macro getName] origin=${mx},${my} width=$mw left=[llength $left] right=[llength $right]"
if {[llength $left] < 100 || ($kind eq "vm" && [llength $right] < 40)} {
    error "local cut did not retain required registered payload"
}
