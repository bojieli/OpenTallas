# el1011-q-seq (2026-10-11, textbook audit class 6): planned macro placement for blocks whose delay lines / stores are
# SRAM macros.  Macros in name order (u_* data-flow order of the generators), filled into columns of at most the core
# height minus 2 * OT_MG_MARGIN; >= OT_MG_CH (20.16 um) channel between macros and between columns, >= OT_MG_MARGIN
# (40 um) to the die edge; the column block centred; R0 only (mirrored macros put pins off track).
set b [ord::get_db_block]
set die [$b getDieArea]
set dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set W [expr {double([$die xMax]) / $dbu}]
set H [expr {double([$die yMax]) / $dbu}]
set ch [expr {[info exists ::env(OT_MG_CH)] ? $::env(OT_MG_CH) : 20.16}]
set mg [expr {[info exists ::env(OT_MG_MARGIN)] ? $::env(OT_MG_MARGIN) : 40.0}]
set ms {}
foreach i [$b getInsts] { if {[[$i getMaster] isBlock]} { lappend ms [list [$i getName] $i] } }
set ms [lsort -index 0 $ms]
if {[llength $ms] == 0} { return }
set cols {}; set col {}; set colh 0.0; set maxh [expr {$H - 2 * $mg}]
foreach e $ms {
    set m [[lindex $e 1] getMaster]
    set mh [expr {double([$m getHeight]) / $dbu}]
    if {[llength $col] > 0 && $colh + $ch + $mh > $maxh} { lappend cols $col; set col {}; set colh 0.0 }
    if {[llength $col] > 0} { set colh [expr {$colh + $ch}] }
    lappend col $e; set colh [expr {$colh + $mh}]
}
lappend cols $col
set tw 0.0; set cws {}; set chs {}
foreach c $cols {
    set cw 0.0; set h 0.0
    foreach e $c { set m [[lindex $e 1] getMaster]
        set cw [expr {max($cw, double([$m getWidth]) / $dbu)}]; set h [expr {$h + double([$m getHeight]) / $dbu + $ch}] }
    lappend cws $cw; lappend chs [expr {$h - $ch}]; set tw [expr {$tw + $cw}]
}
set tw [expr {$tw + $ch * ([llength $cols] - 1)}]
if {$tw > $W - 2 * $mg} { error "macro_grid_place: macro columns ${tw} um wider than the core [expr {$W - 2 * $mg}] um: enlarge the die" }
set x [expr {floor((($W - $tw) / 2.0) / 0.216) * 0.216}]
set k 0
foreach c $cols {
    set y [expr {floor((($H - [lindex $chs $k]) / 2.0) / 0.27) * 0.27}]
    foreach e $c {
        set m [[lindex $e 1] getMaster]
        place_macro -macro_name [lindex $e 0] -location [list $x $y] -orientation R0
        set y [expr {ceil(($y + double([$m getHeight]) / $dbu + $ch) / 0.27) * 0.27}]
    }
    set x [expr {ceil(($x + [lindex $cws $k] + $ch) / 0.216) * 0.216}]
    incr k
}
puts "macro_grid_place: [llength $ms] macros in [llength $cols] columns, block ${tw} um wide"
