# MACRO_PLACEMENT_TCL (el1011-hbm-coll 2026-10-11): planned floorplan of the HIERARCHICAL hfd_coll (OWNER textbook audit:
# the flat r25gq die put 9 slices + 162 SRAMs on one clock tree and let the flow place every macro -> classes 1 + 6).
# 9 hardened ot_hcoll_port tiles (INTERIOR=4 view: core face left, link face right, pins on left/right only) in three
# columns of three, each tile beside the die face of its llk port (port p <-> llk: 0 S0 W, 1 S1 E, 2 S2 S, 3 S3 S, 4 S4 E,
# 5 N0 W, 6 N1 W, 7 N2 W, 8 N3 E; the wrapper's ot_hfd_oreg5 relays carry tile -> pin):
#   west column  x = 10, MY (link face west):  p0 / p5 / p7
#   east column  x = W - 10 - tw, R0 (link face east): p1 / p4 / p8
#   middle column centred: p3 (R0, link east -> S3 pins), p2 (R0 -> S2 pins), p6 (MY, link west -> N1 pins)
# Core std cells use the two ~144 um channels between the columns (each tile's core face looks into one) and the top strip;
# the core's own SRAMs (hub / delivery delay lines, own-delivery queue, rgx banks / sink queues) are packed in rows in the top
# strip, grouped in hierarchy-name order, 20 um channels.  Errors with the needed die height if they do not fit.
set block [ord::get_db_block]
set u [$block getDbUnitsPerMicron]
set die [$block getDieArea]
set W [expr {double([$die dx])/$u}]
set H [expr {double([$die dy])/$u}]
proc ot_put {inst x y orient} {
    upvar u u
    $inst setPlacementStatus PLACED
    $inst setOrient $orient
    $inst setLocation [expr {int(round($x*$u))}] [expr {int(round($y*$u))}]
    # setLocation positions the origin; shift so the transformed bbox lower-left lands on (x, y)
    set bb [$inst getBBox]
    set dx [expr {int(round($x*$u)) - [$bb xMin]}]; set dy [expr {int(round($y*$u)) - [$bb yMin]}]
    if {$dx != 0 || $dy != 0} {
        set loc [$inst getLocation]
        $inst setLocation [expr {[lindex $loc 0] + $dx}] [expr {[lindex $loc 1] + $dy}]
    }
    $inst setPlacementStatus FIRM
}
set tiles {}; set srams {}
foreach inst [$block getInsts] {
    set m [$inst getMaster]
    if {[$m getType] ne "BLOCK"} continue
    if {[$m getName] eq "ot_hcoll_port"} { lappend tiles $inst } else { lappend srams $inst }
}
if {[llength $tiles] != 9} { error "hfd_coll_h MPT: expected 9 ot_hcoll_port tiles, found [llength $tiles]" }
set tm [[lindex $tiles 0] getMaster]
set tw [expr {double([$tm getWidth])/$u}]; set th [expr {double([$tm getHeight])/$u}]
set g 20.0
set ys [list 10.0 [expr {10.0 + $th + $g}] [expr {10.0 + 2*($th + $g)}]]
set xw 10.0; set xe [expr {$W - 10.0 - $tw}]; set xm [expr {round(($W - $tw)/2.0)}]
# port -> {x y orient}
array set plan [list \
    0 [list $xw [lindex $ys 0] MY] 5 [list $xw [lindex $ys 1] MY] 7 [list $xw [lindex $ys 2] MY] \
    1 [list $xe [lindex $ys 0] R0] 4 [list $xe [lindex $ys 1] R0] 8 [list $xe [lindex $ys 2] R0] \
    3 [list $xm [lindex $ys 0] R0] 2 [list $xm [lindex $ys 1] R0] 6 [list $xm [lindex $ys 2] MY]]
foreach inst $tiles {
    set n [$inst getName]
    if {![regexp {g_port\\?\[([0-8])\\?\]} $n -> p]} { error "hfd_coll_h MPT: no port index in $n" }
    lassign $plan($p) x y o
    ot_put $inst $x $y $o
    puts "HFDCOLL_H_TILE p$p $n $x $y $o"
}
# core SRAMs: rows in the top strip
set top_tiles [expr {[lindex $ys 2] + $th}]
set y [expr {$top_tiles + $g}]
set x 10.0
set srams [lsort -dictionary -command {apply {{a b} {string compare -nocase [$a getName] [$b getName]}}} $srams]
set n 0
foreach inst $srams {
    set m [$inst getMaster]
    set mw [expr {double([$m getWidth])/$u}]; set mh [expr {double([$m getHeight])/$u}]
    if {$x + $mw > $W - 10.0} { set x 10.0; set y [expr {$y + $mh + $g}] }
    if {$y + $mh > $H - 10.0} {
        set left [expr {[llength $srams] - $n}]
        set per [expr {int(($W - 20.0 + $g) / ($mw + $g))}]
        set need [expr {$y + ceil(double($left)/$per) * ($mh + $g) + 10.0}]
        error "hfd_coll_h MPT: core SRAM strip full after $n of [llength $srams]; needs die height >= [format %.0f $need] (DH_OVR)"
    }
    ot_put $inst $x $y R0
    set x [expr {$x + $mw + $g}]
    incr n
}
puts "HFDCOLL_H_MPT tiles 9 (${tw}x${th}) core_srams $n top_of_tiles $top_tiles strip_top [format %.1f [expr {$y}]] die ${W}x${H}"
