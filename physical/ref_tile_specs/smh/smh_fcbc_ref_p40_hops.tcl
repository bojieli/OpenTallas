# piece port flops at their pins, FIRM (tools/hbm_accel_smh_physical.py; margin rule: every boundary flop -> pin)
set ::ot_blk [ord::get_db_block]
set ::ot_rows {}
set ::ot_ry [dict create]
foreach r [$::ot_blk getRows] { dict set ::ot_ry [lindex [$r getOrigin] 1] [$r getOrient] }
foreach y [lsort -integer [dict keys $::ot_ry]] { lappend ::ot_rows [list $y [dict get $::ot_ry $y]] }
proc ::ot_place {re xlo xhi ylo yhi} {
    set dbu [$::ot_blk getDbUnitsPerMicron]
    set x0 [expr {int(round(1.08 * $dbu))}]
    set sw [expr {int(round(0.054 * $dbu))}]
    set names {}
    set occ {}
    set rh [expr {int(round(0.27 * $dbu))}]
    foreach i [$::ot_blk getInsts] {
        set n [$i getName]
        if {[regexp $re [string map {"\\" ""} $n]] && [string match *DFF* [[$i getMaster] getName]] &&
            [$i getPlacementStatus] ne "FIRM"} { lappend names $i; continue }
        if {[$i isPlaced] || [$i getPlacementStatus] eq "FIRM"} {
            # any placed cell or macro whose box crosses the window (a macro starting below ylo counts too:
            # front_m2c DPL-0033, u_bmd flops placed over the ring macro whose yMin lay under the window)
            set bb [$i getBBox]
            set hl [expr {[[$i getMaster] isBlock] ? int(round(3.0 * $dbu)) : 0}]   ;# MACRO_PLACE_HALO 3 3
            if {[$bb yMax] + $hl > $ylo * $dbu && [$bb yMin] - $hl <= $yhi * $dbu + $rh &&
                [$bb xMax] + $hl > $xlo * $dbu - $sw && [$bb xMin] - $hl < $xhi * $dbu + $sw} {
                lappend occ [list [expr {[$bb xMin] - $hl}] [expr {[$bb xMax] + $hl}] [expr {[$bb yMin] - $hl}] [expr {[$bb yMax] + $hl}]]
            }
        }
    }
    set names [lsort -command {apply {{a b} {string compare [$a getName] [$b getName]}}} $names]
    set rows {}
    set par 0
    foreach r $::ot_rows {
        set y [lindex $r 0]
        if {$y < $ylo * $dbu || $y > $yhi * $dbu} { continue }
        if {$par % 2 == 0} { lappend rows $r }
        incr par
    }
    set k 0
    set n [llength $names]
    foreach r $rows {
        set y [lindex $r 0]
        set busy {}
        foreach iv $occ { if {[lindex $iv 2] < $y + $rh && [lindex $iv 3] > $y} { lappend busy $iv } }
        set x [expr {$x0 + (int($xlo * $dbu) - $x0 + $sw - 1) / $sw * $sw}]
        while {$k < $n} {
            set inst [lindex $names $k]
            set w [[$inst getMaster] getWidth]
            set w2 [expr {$w + 12 * $sw}]   ;# room for the resizer to upsize a FIRM flop in place
            if {$x + $w2 > int($xhi * $dbu)} { break }
            set hit 0
            foreach iv $busy {
                if {$x < [lindex $iv 1] + $sw && $x + $w2 > [lindex $iv 0] - $sw} { set hit [lindex $iv 1]; break }
            }
            if {$hit} { set x [expr {$x0 + ($hit + $sw - $x0 + $sw - 1) / $sw * $sw}]; continue }
            place_inst -name [$inst getName] -location [list [expr {double($x) / $dbu}] [expr {double($y) / $dbu}]] -orientation [lindex $r 1] -status FIRM
            set x [expr {$x + $w2}]
            incr k
        }
    }
    if {$k < $n} { error "ot_place $re: placed $k of $n in ($xlo $xhi $ylo $yhi)" }
    puts "ot_place $re: $n flops"
}
ot_place {^u_sk0\.g_c\[[0-9]+\]\.(g_d\.h|u\.)} 124 264 420 476
