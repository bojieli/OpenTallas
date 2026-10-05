# v5 (2026-10-05): v4 plus no flank within two tracks of the clk pin (Z11d 2 DRC).
# v4 (2026-10-05): v3 without the clk pin (clock NDR spacing).
# v3 (2026-10-04): v2 plus no flank within one half-track of any M5 pin box.
# v2 (dsrom_q_pin_keepout2.tcl, 2026-10-04): M5 flanks only, 0.096 um deep.  v1 (M4 / M6 over the pin, 0.288 um) left
# ~136 of ~200 detail-route violations against its own obstructions in every route (Z5a / Z6 / Z7): the element router
# escapes the 0.096 um-pitch pins on M4.  The S81 blocker was the M5 jog alone (the abstract has M4 / M6 OBS over every
# pin, and 733 of 734 were accessible).
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
set ot_depth [expr {round(0.096 * $ot_dbu)}]
set ot_p [expr {round(0.048 * $ot_dbu)}]; set ot_hw [expr {round(0.012 * $ot_dbu)}]
# every M5 pin box keyed by its centre x (to skip a neighbour track that is itself a pin)
set ot_pins {}
array set ot_occ {}
array set ot_clk {}
foreach bt [$ot_blk getBTerms] {
    if {[$bt getSigType] in {POWER GROUND}} continue
    # v4: no keepout at the clock pin (its net is routed under the clock non-default rule's wider spacing, so a flank
    # at regular spacing is itself a violation: Z10e's 4 DRC; S81 found the clock pin accessible)
    if {[$bt getName] eq "clk"} {
        foreach bp [$bt getBPins] { foreach box [$bp getBoxes] {
            if {[$box yMax] == $ot_ytop} { set ot_clk(top) [expr {([$box xMin] + [$box xMax]) / 2}] }
            if {[$box yMin] == $ot_ybot} { set ot_clk(bot) [expr {([$box xMin] + [$box xMax]) / 2}] }
        } }
        continue
    }
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
        # v5: no flank within one pin pitch of the clk pin (its NDR wire), Z11d's 2 DRC
        if {[info exists ot_clk($side)] && abs($tc - $ot_clk($side)) <= 2 * $ot_p} continue
        # v3: skip a flank that would touch any M5 pin box (a pin wider than one track, e.g. clk: Z10e left 4 M5
        # spacing violations between flanks and the clk pin)
        set fx0 [expr {$tc - $ot_hw - $ot_hw}]; set fx1 [expr {$tc + $ot_hw + $ot_hw}]
        set hit 0
        foreach q $ot_pins { lassign $q qs qc qx0 qx1; if {$qs eq $side && $qx0 < $fx1 && $qx1 > $fx0} { set hit 1; break } }
        if {$hit} continue
        odb::dbObstruction_create $ot_blk $ot_m5 [expr {$tc - $ot_hw}] $by0 [expr {$tc + $ot_hw}] $by1
        incr ot_n5
    }
}
puts "OT_PIN_KEEPOUT pins=[llength $ot_pins] m5_flank=$ot_n5 m4m6=$ot_n46 depth_um=0.096 version=5"
