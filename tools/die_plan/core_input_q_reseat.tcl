# Repair design may insert geographically remote buffers after the pre-GPL
# NK latch input anchor. Put a detouring unary latch-to-core buffer chain
# beside its real capture pin after resize and let detailed place legalize it.
namespace eval ot_nk_q {
    proc centre {box} {
        return [list [expr {([$box xMin]+[$box xMax])/2}] [expr {([$box yMin]+[$box yMax])/2}]]
    }
    proc distance {a b} {
        lassign $a x y
        lassign $b xx yy
        return [expr {abs($x-$xx)+abs($y-$yy)}]
    }
    proc chain {latch} {
        set net ""
        foreach it [$latch getITerms] {
            if {[[$it getMTerm] getName] eq "Q"} {set net [$it getNet]}
        }
        set buffers {}
        set visited {}
        for {set depth 0} {$depth < 7} {incr depth} {
            if {$net in {"" NULL} || [dict exists $visited $net]} {return {}}
            dict set visited $net 1
            set loads {}
            foreach it [$net getITerms] {if {[$it isInputSignal]} {lappend loads $it}}
            if {[llength $loads] != 1 || [llength [$net getBTerms]]} {return {}}
            set pin [lindex $loads 0]
            set cell [$pin getInst]
            set master [$cell getMaster]
            if {[$master isBlock]} {return [list $pin $buffers]}
            if {![regexp {^(BUF|INV)} [$master getName]] || [$cell getPlacementStatus] in {FIRM LOCKED COVER}} {
                return {}
            }
            lappend buffers $cell
            set drivers {}
            foreach it [$cell getITerms] {if {[$it isOutputSignal]} {lappend drivers [$it getNet]}}
            if {[llength $drivers] != 1} {return {}}
            set net [lindex $drivers 0]
        }
        return {}
    }
    proc face_location {pin dist} {
        set box [[$pin getInst] getBBox]
        lassign [centre [$pin getBBox]] x y
        set options [list \
            [list [expr {abs($x-[$box xMin])}] [expr {[$box xMin]-$dist}] $y] \
            [list [expr {abs([$box xMax]-$x)}] [expr {[$box xMax]+$dist}] $y] \
            [list [expr {abs($y-[$box yMin])}] $x [expr {[$box yMin]-$dist}]] \
            [list [expr {abs([$box yMax]-$y)}] $x [expr {[$box yMax]+$dist}]]]
        return [lrange [lindex [lsort -integer -index 0 $options] 0] 1 end]
    }
    proc reseat {} {
        set block [ord::get_db_block]
        set scale [$block getDbUnitsPerMicron]
        set core [$block getCoreArea]
        set macros {}
        foreach inst [$block getInsts] {
            if {[[$inst getMaster] isBlock]} {lappend macros [$inst getBBox]}
        }
        set nchain 0
        set nbuf 0
        foreach latch [$block getInsts] {
            if {![string match *u_lk_nk_* [$latch getName]] || ![string match DLL* [[$latch getMaster] getName]]} {
                continue
            }
            set trace [chain $latch]
            if {[llength $trace] != 2 || ![llength [lindex $trace 1]]} {continue}
            lassign $trace pin buffers
            set last [centre [$pin getBBox]]
            set at [centre [$latch getBBox]]
            set direct [distance $at $last]
            if {$direct > 35*$scale} {continue}
            set route 0
            foreach cell $buffers {
                set next [centre [$cell getBBox]]
                incr route [distance $at $next]
                set at $next
            }
            incr route [distance $at $last]
            if {$route - $direct < 35*$scale || $route < 2*$direct} {continue}
            set seats {}
            set gap 6
            foreach cell [lreverse $buffers] {
                lassign [face_location $pin [expr {$gap*$scale}]] x y
                set w [[$cell getMaster] getWidth]
                set h [[$cell getMaster] getHeight]
                if {$x < [$core xMin] || $y < [$core yMin] || $x+$w > [$core xMax] || $y+$h > [$core yMax]} {
                    break
                }
                set intersects 0
                foreach other $macros {
                    if {$x < [$other xMax] && $x+$w > [$other xMin] &&
                        $y < [$other yMax] && $y+$h > [$other yMin]} {
                        set intersects 1
                        break
                    }
                }
                if {$intersects} {break}
                lappend seats [list $cell $x $y]
                incr gap 5
            }
            if {[llength $seats] != [llength $buffers]} {continue}
            foreach seat $seats {
                lassign $seat cell x y
                $cell setLocation $x $y
                $cell setPlacementStatus PLACED
            }
            incr nchain
            incr nbuf [llength $seats]
        }
        puts "OT_NK_Q_RESEAT moved $nbuf buffers in $nchain latch-to-core chains"
    }
}
ot_nk_q::reseat
