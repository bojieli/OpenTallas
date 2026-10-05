# Track-aligned successor (2026-10-03, results/uarch/macro_pin_access_audit_20261003): the body of
# physical/abi3/w10_wake_column_place.tcl (left byte-identical) with every macro origin computed per orientation by
# physical/common/ot_macro_track_snap.tcl from the macro's own pins, W/H and the platform tracks, and a
# floorplan-time OT_MACRO_TRACK_ASSERT that fails the run if any macro signal pin centre is off-track.
source [file join [expr {[info exists ::env(OT_SRC_ROOT)] ? $::env(OT_SRC_ROOT) : "/src"}] physical/common/ot_macro_track_snap.tcl]
# Baseline closure companion; unchanged geometry/constraint body from d417de733 physical/abi3/v41_w10_elem_pair_pp_lw700_place.tcl SHA256 7611817b0373dfa8a90b4aad80ae96cc26822591716d59a4bfe8bab18315373f
# POST_MACRO_PLACE hook for the W2 V4.1 w10_elem_pair ROM/MAC neighborhood (tools/v41_w2_romac_pnr.py).
# Places every macro FIRM on the joint site / M4-track grid, then FIXES each ROM output's capture flop
# beside the pin it captures, in the orientation of its row (VDD/VSS rails align).
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
        if {[string map {\\ {}} [$inst getName]] eq $want} { return $inst }
    }
    error "placement hook: no instance $want"
}
proc ot_row_orient {block y dbu} {
    set yi [expr {round($y*$dbu)}]
    foreach row [$block getRows] { if {[lindex [$row getOrigin] 1] == $yi} { return [$row getOrient] } }
    error "No placement row at Y=$y"
}
set ot_macros {
    {g_mac[0].g_pp.u_rom0} 14.160 6.160 R0 0
    {g_mac[0].g_pp.u_rom1} 14.160 73.390 MX 0
    {g_mac[1].g_pp.u_rom0} 863.440 6.160 MY 0
    {g_mac[1].g_pp.u_rom1} 863.440 73.390 R180 0
}
set nfixed 0
set nunused 0
set used [dict create]
foreach {name mx my orient capture} $ot_macros {
    set inst [ot_find $block $name]
    # orientation-aware: the v1 "0 mod 0.048" y snap put every MX/R180 pin 6 nm off the M4 track
    lassign [ot_mts::place $inst $mx $my $orient FIRM] px py
    if {!$capture} { continue }
    set box [$inst getBBox]
    set bx0 [expr {double([$box xMin])/$dbu}]; set bx1 [expr {double([$box xMax])/$dbu}]
    foreach it [$inst getITerms] {
        set mt [$it getMTerm]
        if {![string match rd_out* [$mt getName]]} { continue }
        set net [$it getNet]
        if {$net eq "NULL" || $net eq ""} { continue }
        set ff {}
        foreach o [$net getITerms] {
            set oi [$o getInst]
            if {[string match *DFF* [[$oi getMaster] getName]]} { set ff $oi; break }
        }
        if {$ff eq {}} {
            foreach o [$net getITerms] {
                set oi [$o getInst]
                if {$oi eq $inst} { continue }
                foreach ot [$oi getITerms] {
                    if {![$ot isOutputSignal]} { continue }
                    set n2 [$ot getNet]
                    if {$n2 eq "NULL" || $n2 eq ""} { continue }
                    foreach o2 [$n2 getITerms] {
                        if {[string match *DFF* [[[$o2 getInst] getMaster] getName]]} { set ff [$o2 getInst]; break }
                    }
                    if {$ff ne {}} { break }
                }
                if {$ff ne {}} { break }
            }
        }
        if {$ff eq {}} { incr nunused; continue }
        set xy [$it getAvgXY]
        set pinx [expr {double([lindex $xy 1])/$dbu}]; set piny [expr {double([lindex $xy 2])/$dbu}]
        set fw [expr {double([[$ff getMaster] getWidth])/$dbu}]
        set fh [expr {double([[$ff getMaster] getHeight])/$dbu}]
        set west [expr {abs($pinx-$bx0) < abs($pinx-$bx1)}]
        set y [ot_snap [expr {$piny-$fh/2.0}] $ygrid0 $ypitch]
        # one column first; if the row slot is taken, step outward by one flop width
        for {set col 0} {$col < 6} {incr col} {
            if {$west} { set x [expr {$bx0-2.2-($col+1)*($fw+0.216)}] } else { set x [expr {$bx1+2.2+$col*($fw+0.216)}] }
            set x [ot_snap $x $xgrid0 $xpitch]
            set key "[format %.3f $x],[format %.3f $y]"
            if {![dict exists $used $key]} { break }
        }
        dict set used $key 1
        place_inst -name [$ff getName] -location [format "%.3f %.3f" $x $y] -orientation [ot_row_orient $block $y $dbu] -status FIRM
        incr nfixed
    }
}
ot_mts::assert_on_track -label [file tail [info script]]
puts "OT_W10_ELEM_PLACE macros=[expr {[llength $ot_macros]/5}] fixed_capture_flops=$nfixed"
if {$nfixed + $nunused != 0 || $nunused > 0} { error "capture flop count $nfixed" }
