# SU reducer SAFE: every kept pin flop (u_p*/g_tv first stage) placed FIRM next to its pin after IO placement.
# Procs copied from tools/hbm_accel_smh_physical.py PIN_TCL (claude/hbm-sm-structure-20261005 bd35cd2dc).
# piece port flops at their pins, FIRM (tools/hbm_accel_smh_physical.py; margin rule: every boundary flop -> pin)
set ::ot_blk [ord::get_db_block]
set ::ot_rows {}
set ::ot_ry [dict create]
foreach r [$::ot_blk getRows] { dict set ::ot_ry [lindex [$r getOrigin] 1] [$r getOrient] }
foreach y [lsort -integer [dict keys $::ot_ry]] { lappend ::ot_rows [list $y [dict get $::ot_ry $y]] }
# every flop of re whose D or Q reaches a port (through buffers / inverters) is placed FIRM at its pin: W / E pins
# in an edge strip `depth` um wide at the pin's row, N / S pins in the `depth` um of rows next to that edge at the
# pin's x.  Run before any other FIRM placement in the strips.
proc ::ot_net_port {net dir} {
    for {set d 0} {$d < 4} {incr d} {
        if {$net eq "NULL" || $net eq ""} { return "" }
        set bts [$net getBTerms]
        if {[llength $bts] > 0} { return [lindex $bts 0] }
        set nx "NULL"
        foreach it [$net getITerms] {
            set out [$it isOutputSignal]
            if {($dir eq "q" && $out) || ($dir eq "d" && !$out)} { continue }
            set inst [$it getInst]
            if {![regexp {^(BUF|INV|HB)} [[$inst getMaster] getName]]} { continue }
            foreach o [$inst getITerms] {
                if {![$o isInputSignal] && ![$o isOutputSignal]} { continue }
                if {($dir eq "q" && [$o isOutputSignal]) || ($dir eq "d" && [$o isInputSignal])} { set nx [$o getNet] }
            }
            break
        }
        set net $nx
    }
    return ""
}
proc ::ot_flop_port {inst} {
    set qn "NULL"; set dn "NULL"
    foreach it [$inst getITerms] {
        set mt [[$it getMTerm] getName]
        if {[$it isOutputSignal]} { set qn [$it getNet] } elseif {$mt eq "D"} { set dn [$it getNet] }
    }
    set bt [::ot_net_port $qn q]
    if {$bt eq ""} { set bt [::ot_net_port $dn d] }
    return $bt
}
# first slot from c (dir 1: rightwards, the slot is [c, c + w2]; dir -1: leftwards, the slot is [c - w2, c]) in row y
# clear of every cell placed before the pin placement (tap / boundary cells, FIRM flops)
proc ::ot_skip {c w2 y dir sw} {
    if {![dict exists $::ot_occ $y]} { return $c }
    set ivs [dict get $::ot_occ $y]
    set moved 1
    while {$moved} {
        set moved 0
        foreach iv $ivs {
            lassign $iv a b
            if {$dir > 0} {
                if {$c < $b + $sw && $c + $w2 > $a - $sw} { set c [expr {$b + $sw}]; set moved 1 }
            } else {
                if {$c - $w2 < $b + $sw && $c > $a - $sw} { set c [expr {$a - $sw}]; set moved 1 }
            }
        }
    }
    return $c
}
proc ::ot_pin_place_auto {re depth} {
    set dbu [$::ot_blk getDbUnitsPerMicron]
    set sw [expr {int(round(0.054 * $dbu))}]
    set die [$::ot_blk getDieArea]
    set dw [$die xMax]; set dh [$die yMax]
    set m0 [expr {int(round(1.08 * $dbu))}]
    set dp [expr {int(round($depth / 0.054)) * $sw}]
    # the row-end boundary cells (PHY_EDGE_ROW_*, inserted by the tapcell step) sit at both ends of every row
    set capw 0
    foreach i [$::ot_blk getInsts] {
        if {[string match PHY_EDGE_ROW* [$i getName]] && [[$i getMaster] getWidth] > $capw} { set capw [[$i getMaster] getWidth] }
    }
    set m0 [expr {$m0 + $capw}]
    set ::ot_occ [dict create]
    foreach i [$::ot_blk getInsts] {
        if {[[$i getMaster] isBlock] || ![$i isPlaced]} { continue }
        set bb [$i getBBox]
        dict lappend ::ot_occ [$bb yMin] [list [$bb xMin] [$bb xMax]]
    }
    set E [dict create W {} E {} S {} N {}]
    set skip 0
    foreach i [$::ot_blk getInsts] {
        if {![string match *DFF* [[$i getMaster] getName]]} { continue }
        if {![regexp $re [string map {"\\" ""} [$i getName]]]} { continue }
        set bt [::ot_flop_port $i]
        if {$bt eq ""} { incr skip; continue }
        set bb [$bt getBBox]
        set px [expr {([$bb xMin] + [$bb xMax]) / 2}]; set py [expr {([$bb yMin] + [$bb yMax]) / 2}]
        if {$px < 2 * $m0} { set e W } elseif {$px > $dw - 2 * $m0} { set e E } elseif {$py < 2 * $m0} { set e S } else { set e N }
        dict lappend E $e [list [expr {($e eq "W" || $e eq "E") ? $py : $px}] $i]
    }
    set rows {}
    set par 0
    foreach r $::ot_rows { if {$par % 2 == 0} { lappend rows $r }; incr par }
    set nr [llength $rows]
    set placed 0
    foreach e {W E} {
        set fl [lsort -integer -index 0 [dict get $E $e]]
        if {![llength $fl]} { continue }
        if {$e eq "W"} { set lo $m0; set hi [expr {$m0 + $dp}] } else { set hi [expr {$dw - $m0}]; set lo [expr {$hi - $dp}] }
        set cur [lrepeat $nr [expr {$e eq "W" ? $lo : $hi}]]
        foreach f $fl {
            lassign $f py inst
            set w [[$inst getMaster] getWidth]; set w2 [expr {$w + 12 * $sw}]; set h [[$inst getMaster] getHeight]
            for {set a 0; set b [expr {$nr - 1}]} {$a <= $b} {} {
                set m [expr {($a + $b) / 2}]
                if {[lindex $rows $m 0] + $h / 2 < $py} { set a [expr {$m + 1}] } else { set b [expr {$m - 1}] }
            }
            set r0 [expr {$a >= $nr ? $nr - 1 : $a}]
            set done 0
            for {set s 0} {$s < $nr && !$done} {incr s} {
                foreach r [list [expr {$r0 - $s}] [expr {$r0 + $s}]] {
                    if {$r < 0 || $r >= $nr} { continue }
                    set c [lindex $cur $r]
                    set rr [lindex $rows $r]
                    set c [::ot_skip $c $w2 [lindex $rr 0] [expr {$e eq "W" ? 1 : -1}] $sw]
                    if {$e eq "W"} {
                        if {$c + $w2 > $hi} { continue }
                        set x $c; lset cur $r [expr {$c + $w2}]
                    } else {
                        if {$c - $w2 < $lo} { continue }
                        set x [expr {$c - $w2}]; lset cur $r [expr {$c - $w2}]   ;# upsizing grows rightwards: keep the room on the pin side
                    }
                    place_inst -name [$inst getName] -location [list [expr {double($x) / $dbu}] [expr {double([lindex $rr 0]) / $dbu}]] -orientation [lindex $rr 1] -status FIRM
                    set done 1; incr placed; break
                }
            }
            if {!$done} { error "ot_pin_place_auto $re: no room on $e for [$inst getName]" }
        }
    }
    foreach e {S N} {
        set fl [lsort -integer -index 0 [dict get $E $e]]
        if {![llength $fl]} { continue }
        set er {}
        foreach r $rows {
            set y [lindex $r 0]
            if {($e eq "S" && $y >= $m0 && $y < $m0 + $dp) || ($e eq "N" && $y + 270 <= $dh - $m0 && $y + 270 > $dh - $m0 - $dp)} { lappend er $r }
        }
        if {$e eq "N"} { set er [lreverse $er] }
        set ne [llength $er]
        if {!$ne} { error "ot_pin_place_auto: no rows on $e" }
        set cur [lrepeat $ne [expr {$m0 + $dp}]]
        set lim [expr {$dw - $m0 - $dp}]
        # CRASH-TRIAGE 2026-10-08: placements are collected per row and committed at the end.  A flop that finds no
        # room right of its pin in any row (pins crowded toward the edge end: the TT/cgfix re-routes' 3_1 placement
        # moved the S pins and hit "no room on S") goes to the least-filled row past the limit, and that row is then
        # packed back leftwards (each flop keeps its order, right end <= the next flop's left edge / the limit, clear
        # of the tap cells).  Rows without an overflow are untouched, so a layout that fitted before is unchanged.
        set rowp [lrepeat $ne {}]
        set over [lrepeat $ne 0]
        set k 0
        foreach f $fl {
            lassign $f px inst
            set w [[$inst getMaster] getWidth]; set w2 [expr {$w + 12 * $sw}]
            set done 0
            for {set t 0} {$t < $ne && !$done} {incr t} {
                set r [expr {($k + $t) % $ne}]
                set c [lindex $cur $r]
                set x [expr {$px - $w / 2}]
                set x [expr {$m0 + ($x - $m0) / $sw * $sw}]
                if {$x < $c} { set x $c }
                set rr [lindex $er $r]
                set x [::ot_skip $x $w2 [lindex $rr 0] 1 $sw]
                if {$x + $w2 > $lim} { continue }
                lset rowp $r [concat [lindex $rowp $r] [list [list $x $w2 $inst]]]
                lset cur $r [expr {$x + $w2}]
                set done 1
            }
            if {!$done} {
                set r 0
                for {set t 1} {$t < $ne} {incr t} { if {[lindex $cur $t] < [lindex $cur $r]} { set r $t } }
                set x [lindex $cur $r]
                lset rowp $r [concat [lindex $rowp $r] [list [list $x $w2 $inst]]]
                lset cur $r [expr {$x + $w2}]
                lset over $r 1
            }
            incr k
        }
        for {set r 0} {$r < $ne} {incr r} {
            set rr [lindex $er $r]
            set items [lindex $rowp $r]
            if {[lindex $over $r]} {
                set rl $lim
                for {set q [expr {[llength $items] - 1}]} {$q >= 0} {incr q -1} {
                    lassign [lindex $items $q] x w2 inst
                    set rt [expr {$x + $w2 > $rl ? $rl : $x + $w2}]
                    set rt [expr {$m0 + ($rt - $m0) / $sw * $sw}]
                    set rt [::ot_skip $rt $w2 [lindex $rr 0] -1 $sw]
                    set x [expr {$rt - $w2}]
                    if {$x < $m0 + $dp} { error "ot_pin_place_auto $re: no room on $e for [$inst getName] (row [lindex $rr 0] full after left packing)" }
                    lset items $q [list $x $w2 $inst]
                    set rl $x
                }
            }
            foreach it $items {
                lassign $it x w2 inst
                place_inst -name [$inst getName] -location [list [expr {double($x) / $dbu}] [expr {double([lindex $rr 0]) / $dbu}]] -orientation [lindex $rr 1] -status FIRM
                incr placed
            }
        }
    }
    puts "ot_pin_place_auto $re: $placed flops at their pins (W [llength [dict get $E W]] E [llength [dict get $E E]] S [llength [dict get $E S]] N [llength [dict get $E N]]), $skip without a port"
}
# the 3_1 skip-io global placement left every std cell PLACED: free them so the pin strips are empty (3_3 re-places)
foreach ot_i [$::ot_blk getInsts] {
    if {![[$ot_i getMaster] isBlock] && [$ot_i getPlacementStatus] eq "PLACED"} { $ot_i setPlacementStatus NONE }
}
ot_pin_place_auto {^(u_p|g_tv)} 14
orfs_write_db $::env(RESULTS_DIR)/3_2_place_iop.odb
