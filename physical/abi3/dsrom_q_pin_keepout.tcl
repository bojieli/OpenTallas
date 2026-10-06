# DSROM q-element edge-pin access keepout (2026-10-04, S81 die finding: xs_q1[151] of the routed q abstract had no
# die-level access point, boxed in by the element's own route: an M5 jog ending 0.024 um from the pin inside the
# 0.04 um end-of-line window, M6 over and M4 under it).  POST_DETAIL_PLACE hook (before global route): the PG check
# hook, unchanged, then for every signal pin on M5 at the die's top or bottom edge, routing obstructions inside a
# DEPTH band at that edge (outside the core rows): M5 on the two adjacent free tracks (pin centre +- one 0.048 um
# pitch, 0.024 wide, skipped where another pin sits) and M4 / M6 over the pin +- one pitch.  The element route then
# reaches each pin straight up its own M5 track.  The abstract writer removes every obstruction before
# write_abstract_lef (they are a routing constraint, not metal): tools/dsrom_q_abstract.tcl.
source /src/physical/abi3/check_pg_before_route.tcl
set ot_blk [ord::get_db_block]
set ot_tech [ord::get_db_tech]
set ot_dbu [$ot_tech getDbUnitsPerMicron]
set ot_m4 [$ot_tech findLayer M4]; set ot_m5 [$ot_tech findLayer M5]; set ot_m6 [$ot_tech findLayer M6]
set ot_die [$ot_blk getDieArea]
set ot_ytop [$ot_die yMax]; set ot_ybot [$ot_die yMin]
set ot_depth [expr {round(0.288 * $ot_dbu)}]
set ot_p [expr {round(0.048 * $ot_dbu)}]; set ot_hw [expr {round(0.012 * $ot_dbu)}]
# every M5 pin box keyed by its centre x (to skip a neighbour track that is itself a pin)
set ot_pins {}
array set ot_occ {}
foreach bt [$ot_blk getBTerms] {
    if {[$bt getSigType] in {POWER GROUND}} continue
    foreach bp [$bt getBPins] {
        foreach box [$bp getBoxes] {
            if {[$box getTechLayer] ne $ot_m5} continue
            set x0 [$box xMin]; set x1 [$box xMax]; set y0 [$box yMin]; set y1 [$box yMax]
            if {$y1 == $ot_ytop} { set side top } elseif {$y0 == $ot_ybot} { set side bot } else continue
            set xc [expr {($x0 + $x1) / 2}]
            set ot_occ($side,$xc) 1
            lappend ot_pins [list $side $xc $x0 $x1]
        }
    }
}
set ot_n5 0; set ot_n46 0
foreach p $ot_pins {
    lassign $p side xc x0 x1
    if {$side eq "top"} { set by0 [expr {$ot_ytop - $ot_depth}]; set by1 $ot_ytop } else { set by0 $ot_ybot; set by1 [expr {$ot_ybot + $ot_depth}] }
    foreach d [list -$ot_p $ot_p] {
        set tc [expr {$xc + $d}]
        if {[info exists ot_occ($side,$tc)]} continue
        odb::dbObstruction_create $ot_blk $ot_m5 [expr {$tc - $ot_hw}] $by0 [expr {$tc + $ot_hw}] $by1
        incr ot_n5
    }
    foreach l [list $ot_m4 $ot_m6] {
        odb::dbObstruction_create $ot_blk $l [expr {$x0 - $ot_p}] $by0 [expr {$x1 + $ot_p}] $by1
        incr ot_n46
    }
}
puts "OT_PIN_KEEPOUT pins=[llength $ot_pins] m5_flank=$ot_n5 m4m6=$ot_n46 depth_um=0.288"
