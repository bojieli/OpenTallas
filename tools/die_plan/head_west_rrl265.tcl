# West tap 61 staged reset insertion. The check mode reads only the loaded block.
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

proc west_d51_265_peer {driver master pin} {
    set net [$driver getNet]
    if {$net eq "NULL" || [$net isSpecial] || [$net getWire] ne "NULL" ||
        [llength [$net getBTerms]] || [llength [$net getITerms]] != 2} {
        error "West rrl265 expected a single-load, unrouted buffer branch"
    }
    set peer "NULL"
    foreach term [$net getITerms] {
        if {$term ne $driver} { set peer $term }
    }
    if {$peer eq "NULL" || [$peer getIoType] ne "INPUT" ||
        [[$peer getMTerm] getName] ne $pin} {
        error "West rrl265 unexpected branch destination"
    }
    set instance [$peer getInst]
    if {![string match u_rrl_265/* [$instance getName]] ||
        [[$instance getMaster] getName] ne $master} {
        error "West rrl265 branch buffer type or scope changed"
    }
    return $instance
}

proc west_d51_265_manhattan {a b} {
    lassign $a ax ay
    lassign $b bx by
    return [expr {abs($ax-$bx) + abs($ay-$by)}]
}

proc west_d51_265_clear {macros a b margin} {
    lassign $a ax ay
    lassign $b bx by
    foreach corner [list [list $ax $by] [list $bx $ay]] {
        set clear 1
        foreach pair [list [list $a $corner] [list $corner $b]] {
            lassign [lindex $pair 0] px py
            lassign [lindex $pair 1] qx qy
            set x [expr {min($px,$qx)}]
            set y [expr {min($py,$qy)}]
            foreach macro $macros {
                if {[west_d51_265_overlap $macro $x $y [expr {abs($qx-$px)}] [expr {abs($qy-$py)}] $margin]} {
                    set clear 0
                    break
                }
            }
            if {!$clear} { break }
        }
        if {$clear} { return 1 }
    }
    return 0
}

proc west_d51_265_buffer {mode} {
    if {$mode ni {check apply}} { error "expected check or apply" }
    set block [ord::get_db_block]
    set dbu [$block getDbUnitsPerMicron]
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
    set source [west_d51_265_peer [$gate findITerm Y] BUFx3_ASAP7_75t_R A]
    set old [[$source findITerm Y] getNet]
    set load [west_d51_265_peer [$source findITerm Y] BUFx16f_ASAP7_75t_R A]
    west_d51_265_cut [[$load findITerm Y] getNet] [list "[$load getName]/Y" {u_rrl_265/q$_DFF_P_/D}]
    west_d51_265_cut [[$capture findITerm QN] getNet] [list {u_rrl_265/q$_DFF_P_/QN} u_rrl_265/_2_/A]
    set tap [[$output findITerm Y] getNet]
    west_d51_265_cut $tap {u_rrl_265/_2_/Y}
    if {[$tap getName] ne "rst_n_t61"} { error "West rrl265 gated reset terminal changed" }
    set master [[ord::get_db] findMaster BUFx6f_ASAP7_75t_R]
    if {$master eq "NULL"} { error "West rrl265 buffer master missing" }
    set w [$master getWidth]
    set h [$master getHeight]
    set halo [expr {round(2.16*$dbu)}]
    set seats {}
    set points [list [$source getLocation]]
    set macro_boxes {}
    foreach instance [$block getInsts] {
        if {[[$instance getMaster] isBlock]} { lappend macro_boxes [$instance getBBox] }
    }
    foreach {num ux uy orient} {1 848.934 1241.730 MX 2 824.958 1341.360 R0} {
        set x [expr {round($ux*$dbu)}]
        set y [expr {round($uy*$dbu)}]
        set name ot_d51_rrl265_s$num
        set nname ot_d51_rrl265_n$num
        if {[$block findInst $name] ne "NULL" || [$block findNet $nname] ne "NULL"} {
            error "West rrl265 candidate already present"
        }
        set row_ok 0
        foreach row [$block getRows] {
            lassign [$row getOrigin] rx ry
            set pitch [$row getSpacing]
            if {$ry == $y && [$row getOrient] eq $orient && $pitch > 0 && $x >= $rx && ($x-$rx)%$pitch == 0
                && $x+$w <= $rx+$pitch*[$row getSiteCount] && [[$row getSite] getHeight] == $h} {
                set row_ok 1
                break
            }
        }
        if {!$row_ok} { error "West rrl265 candidate row unavailable" }
        foreach instance [$block getInsts] {
            set clear [expr {[[$instance getMaster] isBlock] ? $halo : 0}]
            if {[west_d51_265_overlap [$instance getBBox] $x $y $w $h $clear]} {
                error "West rrl265 seat overlaps [$instance getName]"
            }
        }
        foreach blockage [$block getBlockages] {
            if {![$blockage isSoft] && [west_d51_265_overlap [$blockage getBBox] $x $y $w $h 0]} {
                error "West rrl265 site obstructed"
            }
        }
        lappend seats [list $name $nname $x $y $orient]
        lappend points [list $x $y]
    }
    lappend points [$load getLocation]
    set old_length [west_d51_265_manhattan [lindex $points 0] [lindex $points end]]
    set hops {}
    foreach a [lrange $points 0 end-1] b [lrange $points 1 end] {
        set length [west_d51_265_manhattan $a $b]
        if {2*$length >= $old_length || $length > 405*$dbu
            || ![west_d51_265_clear $macro_boxes $a $b $halo]} {
            error "West rrl265 reviewed seats do not shorten the current macro-clear branch"
        }
        lappend hops [format %.3f [expr {double($length)/$dbu}]]
    }
    puts "WEST_D51_RRL265 $mode guarded same-age inputs, single load, idle tap61; old [format %.3f [expr {double($old_length)/$dbu}]] um; new hops $hops um"
    if {$mode eq "check"} { return }
    set prev $old
    foreach seat $seats {
        lassign $seat name nname x y orient
        set cell [odb::dbInst_create $block $master $name]
        set wire [odb::dbNet_create $block $nname]
        $cell setOrient $orient
        $cell setLocation $x $y
        $cell setPlacementStatus FIRM
        [$cell findITerm A] connect $prev
        [$cell findITerm Y] connect $wire
        foreach pin [$source getITerms] {
            if {[$pin getSigType] in {POWER GROUND} && [$pin getNet] ne "NULL"} {
                [$cell findITerm [[$pin getMTerm] getName]] connect [$pin getNet]
            }
        }
        set prev $wire
    }
    set a [$load findITerm A]
    $a disconnect
    $a connect $prev
    check_placement -verbose
}
