# West tap 61 staged reset insertion, STRUCTURE-DERIVED (C-RRL265-WEST, 2026-11-26).  Default off: only staged by gen_phys.py
# post_dpl_hook_lines with OT_HEAD_WEST_RRL265=1 on hd_lep0N_w.  The check mode reads only the loaded block.
#
# Intent (unchanged): the same-age reset gate u_rrl_265 drives the capture flop u_rrl_265/q$_DFF_P_ (tap 61, idle) over a branch that
# placement left long.  The first form of this hook asserted ONE buffer shape (gate -> BUFx3 -> BUFx16f -> D) and fixed seat
# coordinates, so it failed on any other placement ("unexpected branch destination": W11 + ffbe77 has gate -> place59499 (BUFx3) -> D).
# This form walks the branch from the netlist (gate Y net -> single sink -> optional private buffers -> capture D), measures every hop
# (Manhattan between the two instance origins), and inserts ceil(len/leg)-1 buffers into each hop longer than the leg bound, seated by a
# row/occupancy search around evenly spaced points on a macro-clear L route.  A branch already inside the bound is left alone.
# Bounds: leg <= OT_HEAD_WEST_RRL265_LEG_UM (default 138.402, the reviewed c93d33b guard leg), and always <= 405 um (LEG405).
set ::west_d51_265_leg_um 138.402
if {[info exists ::env(OT_HEAD_WEST_RRL265_LEG_UM)] && $::env(OT_HEAD_WEST_RRL265_LEG_UM) ne ""} {
    set ::west_d51_265_leg_um $::env(OT_HEAD_WEST_RRL265_LEG_UM)
}
set ::west_d51_265_scope u_rrl_265/
set ::west_d51_265_max_buffers 6

proc west_d51_265_cut {net expected} {
    if {$net eq "NULL" || [$net isSpecial] || [$net getWire] ne "NULL" || [llength [$net getBTerms]]} {
        error "West rrl265 missing unrouted signal branch"
    }
    set actual {}
    foreach it [$net getITerms] { lappend actual "[[$it getInst] getName]/[[$it getMTerm] getName]" }
    if {[lsort $actual] ne [lsort $expected]} { error "West rrl265 signal terminals changed" }
}

proc west_d51_265_overlap {bbox x y w h margin} {
    expr {$x < [$bbox xMax]+$margin && $x+$w > [$bbox xMin]-$margin
        && $y < [$bbox yMax]+$margin && $y+$h > [$bbox yMin]-$margin}
}

proc west_d51_265_manhattan {a b} {
    lassign $a ax ay
    lassign $b bx by
    return [expr {abs($ax-$bx) + abs($ay-$by)}]
}

# Pure: the corner (of the two L routes a->c->b) whose two legs both clear every macro box {xmin ymin xmax ymax} by margin; "" if none.
proc west_d51_265_clear_corner {macros a b margin} {
    lassign $a ax ay
    lassign $b bx by
    foreach corner [list [list $ax $by] [list $bx $ay]] {
        set clear 1
        foreach pair [list [list $a $corner] [list $corner $b]] {
            lassign [lindex $pair 0] px py
            lassign [lindex $pair 1] qx qy
            set x [expr {min($px,$qx)}]
            set y [expr {min($py,$qy)}]
            set w [expr {abs($qx-$px)}]
            set h [expr {abs($qy-$py)}]
            foreach m $macros {
                lassign $m x0 y0 x1 y1
                if {$x < $x1+$margin && $x+$w > $x0-$margin && $y < $y1+$margin && $y+$h > $y0-$margin} { set clear 0; break }
            }
            if {!$clear} { break }
        }
        if {$clear} { return $corner }
    }
    return ""
}

# Pure: n-1 evenly spaced points along a->corner->b (n legs).
proc west_d51_265_route_points {a corner b n} {
    set l1 [west_d51_265_manhattan $a $corner]
    set total [expr {$l1 + [west_d51_265_manhattan $corner $b]}]
    set pts {}
    for {set j 1} {$j < $n} {incr j} {
        set d [expr {double($total) * $j / $n}]
        if {$d <= $l1} {
            lassign $a px py
            lassign $corner qx qy
            set f [expr {$l1 > 0 ? $d / $l1 : 0.0}]
        } else {
            lassign $corner px py
            lassign $b qx qy
            set f [expr {($d - $l1) / double($total - $l1)}]
        }
        lappend pts [list [expr {round($px + ($qx-$px)*$f)}] [expr {round($py + ($qy-$py)*$f)}]]
    }
    return $pts
}

# Pure: number of buffers a hop of len needs so every leg <= leg (both in the same unit).
proc west_d51_265_need {len leg} {
    if {$leg <= 0} { error "West rrl265 leg bound must be positive" }
    return [expr {max(0, int(ceil(double($len)/$leg - 1e-9)) - 1)}]
}

# Walk the branch from the gate output to the capture D pin.  Returns {nodes hops}: nodes = instances [gate b1 .. bk capture], hops =
# list of {driver_inst sink_iterm net}.  Every net on the way must be an unrouted single-load signal net; every intermediate cell a
# private (scope) buffer.  Anything else is a structure change and errors.
proc west_d51_265_walk {gate capture} {
    set nodes [list $gate]
    set hops {}
    set drv $gate
    for {set k 0} {$k <= $::west_d51_265_max_buffers} {incr k} {
        set out [[$drv findITerm Y] getNet]
        if {$out eq "NULL" || [$out isSpecial] || [$out getWire] ne "NULL" || [llength [$out getBTerms]]} {
            error "West rrl265 expected an unrouted signal branch"
        }
        set sinks {}
        foreach t [$out getITerms] { if {[$t getIoType] eq "INPUT" && [$t getSigType] eq "SIGNAL"} { lappend sinks $t } }
        if {[llength $sinks] != 1} { error "West rrl265 branch is not single-load ([llength $sinks] sinks on [$out getName])" }
        set sink [lindex $sinks 0]
        set inst [$sink getInst]
        lappend hops [list $drv $sink $out]
        lappend nodes $inst
        if {$inst eq $capture} {
            if {[[$sink getMTerm] getName] ne "D"} { error "West rrl265 branch ends on [[$sink getMTerm] getName], not the capture D pin" }
            return [list $nodes $hops]
        }
        if {!([string match ${::west_d51_265_scope}* [$inst getName]] || [string match ot_d51_rrl265_s* [$inst getName]]) ||
            ![regexp {^BUF} [[$inst getMaster] getName]] ||
            [[$sink getMTerm] getName] ne "A"} {
            error "West rrl265 unexpected branch destination [$inst getName]/[[$sink getMTerm] getName] ([[$inst getMaster] getName])"
        }
        set drv $inst
    }
    error "West rrl265 branch longer than $::west_d51_265_max_buffers buffers"
}

# Seat search: nearest legal site (x y orient row) for a w x h cell around the ideal point; occupancy from instances (macro halo),
# hard blockages and the seats already chosen.  Row intervals are built once per call from the instances in the search window.
proc west_d51_265_seat {block ideal w h halo taken win} {
    lassign $ideal ix iy
    set lo_y [expr {$iy - $win}]
    set hi_y [expr {$iy + $win}]
    set lo_x [expr {$ix - $win - $w}]
    set hi_x [expr {$ix + $win + $w}]
    set rows {}
    foreach row [$block getRows] {
        lassign [$row getOrigin] rx ry
        if {$ry + $h < $lo_y || $ry > $hi_y} { continue }
        if {[[$row getSite] getHeight] != $h || [$row getSpacing] <= 0} { continue }
        lappend rows [list $rx $ry [$row getSpacing] [$row getSiteCount] [$row getOrient]]
    }
    set boxes {}
    foreach inst [$block getInsts] {
        set bb [$inst getBBox]
        set m [expr {[[$inst getMaster] isBlock] ? $halo : 0}]
        if {[$bb xMax]+$m < $lo_x || [$bb xMin]-$m > $hi_x || [$bb yMax]+$m < $lo_y || [$bb yMin]-$m > $hi_y} { continue }
        lappend boxes [list [expr {[$bb xMin]-$m}] [expr {[$bb yMin]-$m}] [expr {[$bb xMax]+$m}] [expr {[$bb yMax]+$m}]]
    }
    foreach bl [$block getBlockages] {
        if {[$bl isSoft]} { continue }
        set bb [$bl getBBox]
        lappend boxes [list [$bb xMin] [$bb yMin] [$bb xMax] [$bb yMax]]
    }
    foreach t $taken { lappend boxes $t }
    set best {}
    set bestcost 1e30
    foreach r $rows {
        lassign $r rx ry pitch count orient
        set ivs {}
        foreach b $boxes {
            lassign $b x0 y0 x1 y1
            if {$y0 < $ry + $h && $y1 > $ry} { lappend ivs [list $x0 $x1] }
        }
        set ivs [lsort -integer -index 0 $ivs]
        set row_end [expr {$rx + $pitch*$count}]
        set cur $rx
        lappend ivs [list $row_end $row_end]
        foreach iv $ivs {
            lassign $iv x0 x1
            set g1 [expr {min($x0, $row_end)}]
            if {$g1 - $cur >= $w} {
                set kmin [expr {int(ceil(double($cur - $rx)/$pitch))}]
                set kmax [expr {int(floor(double($g1 - $w - $rx)/$pitch))}]
                if {$kmax >= $kmin} {
                    set k [expr {int(round(double($ix - $rx)/$pitch))}]
                    set k [expr {min($kmax, max($kmin, $k))}]
                    set x [expr {$rx + $k*$pitch}]
                    set cost [expr {abs($x-$ix) + abs($ry-$iy)}]
                    if {$cost < $bestcost} { set bestcost $cost; set best [list $x $ry $orient] }
                }
            }
            if {$x1 > $cur} { set cur $x1 }
        }
    }
    return $best
}

# Plan: list of {hop_index buffer_name net_name x y orient} for the whole branch, or {} when every leg is already inside the bound.
# Also puts the old / new hop lengths.  Errors when no macro-clear route or no seat exists, or the result would not satisfy the bound.
proc west_d51_265_plan {block gate capture mode} {
    set dbu [$block getDbUnitsPerMicron]
    set leg [expr {min(double($::west_d51_265_leg_um), 405.0) * $dbu}]
    set walk [west_d51_265_walk $gate $capture]
    lassign $walk nodes hops
    set master [[ord::get_db] findMaster BUFx6f_ASAP7_75t_R]
    if {$master eq "NULL"} { error "West rrl265 buffer master missing" }
    set w [$master getWidth]
    set h [$master getHeight]
    set halo [expr {round(2.16*$dbu)}]
    set macro_boxes {}
    foreach inst [$block getInsts] {
        if {[[$inst getMaster] isBlock]} {
            set bb [$inst getBBox]
            lappend macro_boxes [list [$bb xMin] [$bb yMin] [$bb xMax] [$bb yMax]]
        }
    }
    set old {}
    set seats {}
    set taken {}
    set new {}
    set count 0
    foreach hop $hops {
        lassign $hop drv sink net
        set a [$drv getLocation]
        set b [[$sink getInst] getLocation]
        set len [west_d51_265_manhattan $a $b]
        lappend old [format %.3f [expr {double($len)/$dbu}]]
        set need [west_d51_265_need $len $leg]
        if {$need == 0} { lappend new [format %.3f [expr {double($len)/$dbu}]]; continue }
        set corner [west_d51_265_clear_corner $macro_boxes $a $b $halo]
        if {$corner eq ""} { error "West rrl265 no macro-clear route for a [expr {double($len)/$dbu}] um hop" }
        set chain [list $a]
        foreach p [west_d51_265_route_points $a $corner $b [expr {$need+1}]] {
            set s {}
            foreach win [list [expr {round(10.0*$dbu)}] [expr {round(30.0*$dbu)}]] {
                set s [west_d51_265_seat $block $p $w $h $halo $taken $win]
                if {$s ne ""} { break }
            }
            if {$s eq ""} { error "West rrl265 no free site near [format %.3f,%.3f [expr {double([lindex $p 0])/$dbu}] [expr {double([lindex $p 1])/$dbu}]]" }
            lassign $s x y orient
            incr count
            set name ot_d51_rrl265_s$count
            set nname ot_d51_rrl265_n$count
            if {[$block findInst $name] ne "NULL" || [$block findNet $nname] ne "NULL"} { error "West rrl265 candidate already present" }
            lappend taken [list $x $y [expr {$x+$w}] [expr {$y+$h}]]
            lappend seats [list [llength $old] $name $nname $x $y $orient $sink $net]
            lappend chain [list $x $y]
        }
        lappend chain $b
        foreach p [lrange $chain 0 end-1] q [lrange $chain 1 end] {
            set l [west_d51_265_manhattan $p $q]
            if {$l > $leg || $l > 405*$dbu || [west_d51_265_clear_corner $macro_boxes $p $q $halo] eq ""} {
                error "West rrl265 seated legs do not meet the bound ([format %.3f [expr {double($l)/$dbu}]] um)"
            }
            lappend new [format %.3f [expr {double($l)/$dbu}]]
        }
    }
    if {[llength $seats] > $::west_d51_265_max_buffers} { error "West rrl265 more than $::west_d51_265_max_buffers buffers needed" }
    puts "WEST_D51_RRL265 $mode branch [llength $hops] hops, [expr {[llength $nodes]-2}] existing buffers; old hops $old um; new legs $new um; [llength $seats] buffers"
    return $seats
}

proc west_d51_265_buffer {mode} {
    if {$mode ni {check apply}} { error "expected check or apply" }
    set block [ord::get_db_block]
    foreach {role name master} {
        gate u_rrl_265/_3_ AND2x4_ASAP7_75t_R
        capture {u_rrl_265/q$_DFF_P_} DFFHQNx1_ASAP7_75t_R
        output u_rrl_265/_2_ INVx1_ASAP7_75t_R
    } {
        set item [$block findInst $name]
        if {$item eq "NULL" || [[$item getMaster] getName] ne $master} { error "West rrl265 $role identity changed" }
        set $role $item
    }
    west_d51_265_cut [[$gate findITerm A] getNet] {u_rrl_264/_1_/Y u_rrl_265/_3_/A}
    west_d51_265_cut [[$gate findITerm B] getNet] {u_srl_264/_1_/Y u_rrl_265/_3_/B}
    west_d51_265_cut [[$capture findITerm QN] getNet] [list {u_rrl_265/q$_DFF_P_/QN} u_rrl_265/_2_/A]
    set tap [[$output findITerm Y] getNet]
    west_d51_265_cut $tap {u_rrl_265/_2_/Y}
    if {[$tap getName] ne "rst_n_t61"} { error "West rrl265 gated reset terminal changed" }
    set seats [west_d51_265_plan $block $gate $capture $mode]
    if {$mode eq "check" || [llength $seats] == 0} { return }
    set master [[ord::get_db] findMaster BUFx6f_ASAP7_75t_R]
    set groups {}
    foreach seat $seats {
        lassign $seat hop name nname x y orient sink net
        dict lappend groups $hop $seat
    }
    foreach hop [dict keys $groups] {
        set prev ""
        set sink ""
        foreach seat [dict get $groups $hop] {
            lassign $seat idx name nname x y orient sink net
            if {$prev eq ""} { set prev $net }
            set cell [odb::dbInst_create $block $master $name]
            set wire [odb::dbNet_create $block $nname]
            $cell setOrient $orient
            $cell setLocation $x $y
            $cell setPlacementStatus FIRM
            [$cell findITerm A] connect $prev
            [$cell findITerm Y] connect $wire
            foreach pin [$gate getITerms] {
                if {[$pin getSigType] in {POWER GROUND} && [$pin getNet] ne "NULL"} {
                    [$cell findITerm [[$pin getMTerm] getName]] connect [$pin getNet]
                }
            }
            set prev $wire
        }
        $sink disconnect
        $sink connect $prev
    }
    check_placement -verbose
    # re-walk: the branch must still be one single-load chain ending on D with every leg inside the bound
    set dbu [$block getDbUnitsPerMicron]
    lassign [west_d51_265_walk $gate $capture] nodes hops
    set legs {}
    foreach hop $hops {
        set l [west_d51_265_manhattan [[lindex $hop 0] getLocation] [[[lindex $hop 1] getInst] getLocation]]
        if {$l > $::west_d51_265_leg_um*$dbu} { error "West rrl265 applied leg [expr {double($l)/$dbu}] um exceeds the bound" }
        lappend legs [format %.3f [expr {double($l)/$dbu}]]
    }
    puts "WEST_D51_RRL265 applied: [llength $seats] buffers, legs $legs um, placement legal"
}
