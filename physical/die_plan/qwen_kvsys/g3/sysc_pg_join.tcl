# SYS_C planned PDN seam joins. Source immediately after pdngen, before placement.
# Only collinear, same-net M5/M7 anchors across the PHY's two horizontal
# boundaries may be joined. Every added rectangle stays outside the PHY body.
# VDDPHY is never modified; common VSS may abut its existing M7 ground pins.
namespace eval sysc_pg_join {
proc outside {r phy} {
    lassign $r x0 y0 x1 y1; lassign $phy px0 py0 px1 py1
    return [expr {!($x0 < $px1 && $x1 > $px0 && $y0 < $py1 && $y1 > $py0)}]
}
proc apply {} {
    set b [ord::get_db_block]; set tech [ord::get_db_tech]
    set dbu [$b getDbUnitsPerMicron]
    set inst [$b findInst u_bound.u_ucie_rom]
    if {$inst eq "NULL"} {error "SYS_C PG join requires exact actual PHY instance"}
    set box [$inst getBBox]
    set phy [list [$box xMin] [$box yMin] [$box xMax] [$box yMax]]
    lassign $phy px0 py0 px1 py1
    set columns [dict create]; set foreign [dict create]
    foreach nn {VDD VSS VDDPHY} {
        set net [$b findNet $nn]
        if {$net eq "NULL"} {error "SYS_C PG net missing: $nn"}
        foreach wire [$net getSWires] {
            foreach shape [$wire getWires] {
                if {[$shape isVia]} {continue}
                set ln [[$shape getTechLayer] getName]
                if {$ln ni {M5 M7}} {continue}
                set r [list [$shape xMin] [$shape yMin] [$shape xMax] [$shape yMax]]
                dict lappend foreign $ln [list $nn $r]
                if {$nn eq "VDDPHY"} {continue}
                set key [list $nn $ln [$shape xMin] [$shape xMax]]
                dict lappend columns $key [list [$shape yMin] [$shape yMax]]
            }
        }
    }
    set maxgap [expr {round(8.64*$dbu)}]
    set proposals {}
    dict for {key spans} $columns {
        lassign $key nn ln x0 x1
        set last {}; set merged {}
        foreach span [lsort -integer -index 0 $spans] {
            lassign $span lo hi
            if {$last ne {} && $lo <= [lindex $last 1]} {
                lset last 1 [expr {max($hi,[lindex $last 1])}]
            } else {
                if {$last ne {}} {lappend merged $last}
                set last $span
            }
        }
        if {$last ne {}} {lappend merged $last}
        set previous {}
        foreach span $merged {
            if {$previous ne {}} {
                set lo [lindex $previous 1];set hi [lindex $span 0]
                set seam [expr {($lo <= $py0 && $hi >= $py0) || ($lo <= $py1 && $hi >= $py1)}]
                if {$seam && $hi > $lo && $hi-$lo <= $maxgap} {
                    set r [list $x0 $lo $x1 $hi]
                    if {![outside $r $phy]} {error "SYS_C PG bridge would enter PHY body: $nn/$ln $r"}
                    lappend proposals [list $nn $ln $r]
                }
            }
            set previous $span
        }
    }
    # Validate all rectangles before changing the DB. Anchors above come from
    # existing same-net conductors with identical cross-sections. Abutment is
    # full-width, without touching another supply or using a routing waiver.
    foreach proposal $proposals {
        lassign $proposal nn ln r;lassign $r x0 y0 x1 y1
        set spacing [[$tech findLayer $ln] getSpacing]
        foreach entry [dict get $foreign $ln] {
            lassign $entry other f
            if {$other eq $nn} {continue}
            lassign $f fx0 fy0 fx1 fy1
            set dx [expr {max($fx0-$x1,$x0-$fx1,0)}]
            set dy [expr {max($fy0-$y1,$y0-$fy1,0)}]
            if {$dx < $spacing && $dy < $spacing} {error "SYS_C PG bridge conflicts with $other/$ln: $r versus $f"}
        }
    }
    set wires [dict create];set records {};set counts [dict create]
    foreach proposal $proposals {
        lassign $proposal nn ln r;lassign $r x0 y0 x1 y1
        if {![dict exists $wires $nn]} {dict set wires $nn [odb::dbSWire_create [$b findNet $nn] ROUTED]}
        odb::dbSBox_create [dict get $wires $nn] [$tech findLayer $ln] $x0 $y0 $x1 $y1 STRIPE
        dict incr counts "$nn/$ln"
        lappend records [format {{"net":"%s","layer":"%s","rect_dbu":[%d,%d,%d,%d]}} $nn $ln $x0 $y0 $x1 $y1]
    }
    set report [file join [pwd] sysc_pg_join.json]
    if {[info exists ::env(OT_SYSC_PG_JOIN_REPORT)]} {set report $::env(OT_SYSC_PG_JOIN_REPORT)}
    set f [open $report w]
    puts $f [format {{"schema":"opentallas.sysc-pg-joins.v1","dbu":%d,"added":%d,"bridges":[%s]}} $dbu [llength $records] [join $records ,]]
    close $f
    puts "SYS_C_PG_JOIN_GENERATED added=[llength $records] counts=$counts; connectivity still required"
}
}
sysc_pg_join::apply
