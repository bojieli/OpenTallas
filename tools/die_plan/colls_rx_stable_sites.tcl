# Reviewed exact standard-row positions for an existing Coll_s RX chain. The
# stock station grid remains in charge of unrelated relay_sites.
namespace eval ::ot_colls_rx_stable {
    proc rect {shape} {
        return [list [$shape xMin] [$shape yMin] [$shape xMax] [$shape yMax]]
    }
    proc overlap {a b} {
        lassign $a ax ay aX aY
        lassign $b bx by bX bY
        expr {$ax < $bX && $aX > $bx && $ay < $bY && $aY > $by}
    }
    proc run {targets mode} {
        set block [ord::get_db_block]
        if {[$block getDbUnitsPerMicron] != 1000} {error "Coll_s RX receiver seat DBU changed"}
        set owners {}
        foreach target $targets {
            lassign $target name x y orient
            if {[dict exists $owners $name]} {error "duplicate Coll_s RX seat $name"}
            set inst [$block findInst $name]
            if {$inst eq "NULL"} {error "missing Coll_s RX FF $name"}
            set master [$inst getMaster]
            if {[$master getName] ne "DFFHQNx1_ASAP7_75t_R" ||
                [$master getWidth] != 1080 || [$master getHeight] != 270} {
                error "Coll_s RX FF footprint changed for $name"
            }
            if {[$inst getPlacementStatus] in {LOCKED FIXED COVER}} {
                error "fixed Coll_s RX FF $name"
            }
            if {$mode eq "retain" && ([$inst getLocation] ne [list $x $y] || [$inst getOrient] ne $orient)} {
                error "Coll_s RX FF moved before DPL: $name"
            }
            dict set owners $name [list $inst $x $y $orient]
        }
        set rows {}
        foreach row [$block getRows] {
            lassign [rect [$row getBBox]] x y X Y
            dict lappend rows $y [list $x $X [$row getOrient]]
        }
        set blocked {}
        foreach b [$block getBlockages] {
            if {![$b isSoft]} {lappend blocked [list [rect [$b getBBox]] blockage]}
        }
        set fixed {}
        foreach inst [$block getInsts] {
            if {[dict exists $owners [$inst getName]] || [$inst getPlacementStatus] ni {FIRM LOCKED FIXED COVER}} {
                continue
            }
            lassign [rect [$inst getBBox]] x y X Y
            if {[[$inst getMaster] isBlock]} {
                lappend blocked [list [list [expr {$x-8640}] [expr {$y-8640}] [expr {$X+8640}] [expr {$Y+8640}]] [$inst getName]]
            } else {
                for {set r [expr {$y/270}] } {$r*270 < $Y} {incr r} {
                    dict lappend fixed $r [list [list $x $y $X $Y] [$inst getName]]
                }
            }
        }
        dict for {name pos} $owners {
            lassign $pos inst x y orient
            set site [list $x $y [expr {$x+1080}] [expr {$y+270}]]
            set legal 0
            if {($x % 54) == 0 && [dict exists $rows $y]} {
                foreach row [dict get $rows $y] {
                    lassign $row a b ro
                    if {$a <= $x && $x+1080 <= $b && (($ro eq "R0") == ($orient in {R0 MY}))} {
                        set legal 1
                        break
                    }
                }
            }
            if {!$legal} {error "Coll_s RX FF $name cannot use the reviewed row"}
            set ri [expr {$y/270}]
            set local [expr {[dict exists $fixed $ri] ? [dict get $fixed $ri] : {}}]
            foreach obstacle [concat $blocked $local] {
                lassign $obstacle box label
                if {[overlap $site $box]} {error "Coll_s RX seat $name intersects $label"}
            }
            dict lappend fixed $ri [list $site $name]
        }
        dict for {name pos} $owners {
            lassign $pos inst x y orient
            if {$mode eq "seed"} {
                if {[$inst getPlacementStatus] eq "FIRM"} {$inst setPlacementStatus PLACED}
                $inst setOrient $orient
                $inst setLocation $x $y
            }
            $inst setPlacementStatus FIRM
        }
        puts "OT_COLLS_RX_STABLE $mode [dict size $owners] exact FF seats"
    }
}
