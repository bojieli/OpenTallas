# Fixed placement regions keep exact native members without creating optimizer groups.
source /work/place_fixed_sites_data.tcl

namespace eval ot_fixed_sites {
    proc bbox {object} {
        set r [$object getBBox]
        return [list [$r xMin] [$r yMin] [$r xMax] [$r yMax]]
    }

    proc targets {block} {
        set wanted {}
        set dbu [$block getDbUnitsPerMicron]
        foreach row $::ot_fixed_sites {
            lassign $row name master
            set rect {}
            foreach coordinate [lrange $row 2 end] {
                set scaled [expr {$coordinate * $dbu}]
                set native [expr {round($scaled)}]
                if {abs($scaled - $native) > 1e-6} {error "Fixed site $name is off the native DBU grid"}
                lappend rect $native
            }
            dict set wanted $name [list $master $rect]
        }
        set members {}
        foreach instance [$block getInsts] {
            set name [string map [list [format %c 92] {}] [$instance getName]]
            if {![dict exists $wanted $name]} {continue}
            if {[dict exists $members $name]} {error "Ambiguous native fixed-site instance $name"}
            dict set members $name $instance
        }
        set result {}
        dict for {name spec} $wanted {
            if {![dict exists $members $name]} {error "Missing native fixed-site instance $name"}
            lassign $spec master rect
            lappend result [list $name [dict get $members $name] $master $rect]
        }
        return $result
    }

    proc fits {instance rect} {
        lassign $rect x y right top
        lassign [bbox $instance] l b r t
        return [expr {$l == $x && $b == $y && $r <= $right && $t == $top}]
    }

    proc reserve {index rect name pitch check} {
        upvar 1 $index reserved
        lassign $rect x y right top
        set start [expr {int(floor(double($y) / $pitch))}]
        set end [expr {int(ceil(double($top) / $pitch))}]
        for {set row $start} {$row < $end} {incr row} {
            if {$check && [dict exists $reserved $row]} {
                foreach other [dict get $reserved $row] {
                    lassign $other l b r t owner
                    if {$l < $right && $r > $x && $b < $top && $t > $y} {
                        error "Fixed-site reservation for $name overlaps $owner"
                    }
                }
            }
            dict lappend reserved $row [list {*}$rect $name]
        }
    }

    proc seed {} {
        set block [ord::get_db_block]
        set targets [targets $block]
        set rows {}
        foreach row [$block getRows] {
            lassign [bbox $row] l y r t
            set site [$row getSite]
            dict lappend rows $y [list $l $r [$row getOrient] [$site getWidth] [$site getHeight]]
        }
        lassign [lindex $targets 0] _ _ _ first
        lassign $first _ bottom _ top
        set pitch [expr {$top - $bottom}]
        set reserved {}
        foreach instance [$block getInsts] {
            if {[$instance getPlacementStatus] in {FIRM LOCKED COVER}} {
                reserve reserved [bbox $instance] [$instance getName] $pitch 0
            }
        }
        foreach ob [$block getBlockages] {
            if {![$ob isSoft]} {reserve reserved [bbox $ob] "hard placement blockage" $pitch 0}
        }

        set matched {}
        foreach entry $targets {
            lassign $entry name instance master rect
            lassign $rect x y right top
            if {[[$instance getMaster] getName] ne $master || [$instance getPlacementStatus] in {FIRM LOCKED COVER}} {
                error "Fixed-site master or prior status changed for $name"
            }
            set orient {}
            if {[dict exists $rows $y]} {
                foreach row [dict get $rows $y] {
                    lassign $row l r o step height
                    if {$l <= $x && $right <= $r && ($x-$l)%$step == 0 && ($right-$x)%$step == 0 && $top-$y == $height} {
                        set orient $o
                        break
                    }
                }
            }
            if {$orient eq {}} {error "No legal native row for fixed site $name"}
            reserve reserved $rect $name $pitch 1
            lappend matched [list $name $instance $orient $rect]
        }
        foreach entry $matched {
            lassign $entry name instance orient rect
            lassign $rect x y
            $instance setOrient $orient
            $instance setLocation $x $y
            $instance setPlacementStatus FIRM
            if {![fits $instance $rect]} {error "Fixed-site footprint mismatch for $name"}
        }
        puts "OT_FIXED_SITES seeded [llength $targets] exact placement seats"
    }

    proc check {} {
        set targets [targets [ord::get_db_block]]
        foreach entry $targets {
            lassign $entry name instance master rect
            if {[$instance getPlacementStatus] ne "FIRM" || ![fits $instance $rect]} {
                error "Fixed-site reservation lost before detailed placement for $name"
            }
        }
        puts "OT_FIXED_SITES retained [llength $targets] exact placement seats"
    }
}
