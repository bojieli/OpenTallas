# pad_abut_wire.tcl (PAD-ABUT-WIRE-1, FABLE-FIX-S81-SERDES2 2026-11-17): a die pin placed on a hard-macro pin is a routed net.
# Class: a macro_pin pad net (die BTerm pin on / abutting the macro pin, dont_touch, e.g. S81 io_pma_tx[543:0], io_pma_tck,
# io_pma_rx[543:0]) needs no routing, so detail route leaves it without a wire, and the ORFS route stage then stops with
# "Design has unrouted nets" (serdes__t13 H17: 0 violations, 0 antenna, then that error on 1089 pad nets; no serdes kit had reached
# this line before).
# Form (POST_DETAIL_ROUTE, before the routed check): every non-special net without a wire that has exactly one BTerm and one ITerm
# of a block instance, whose pin boxes on one routing layer overlap or abut, gets one wire segment of the layer's default width on
# the common centre line from the BTerm box centre to the macro pin box centre: metal that lies inside the two pin shapes.
# Nothing else is touched.  OT_PAD_ABUT_WIRE=0 turns it off.
namespace eval paw {}
proc paw::run {} {
  if {[info exists ::env(OT_PAD_ABUT_WIRE)] && $::env(OT_PAD_ABUT_WIRE) eq "0"} { puts "OT_PAD_ABUT_WIRE off"; return }
  set blk [ord::get_db_block]; set n 0; set skip 0
  foreach net [$blk getNets] {
    if {[$net isSpecial] || [$net getWire] ne "NULL"} continue
    set bts [$net getBTerms]; set its [$net getITerms]
    if {[llength $bts] != 1 || [llength $its] != 1} continue
    set it [lindex $its 0]; if {![[[$it getInst] getMaster] isBlock]} continue
    set done 0
    foreach bp [[lindex $bts 0] getBPins] { foreach b [$bp getBoxes] {
      if {$done} break
      set L [$b getTechLayer]; if {$L eq "NULL" || [$L getType] ne "ROUTING"} continue
      # the macro pin must have a shape on that layer; its placed box is the ITerm bbox
      set onl 0; foreach mp [[$it getMTerm] getMPins] { foreach g [$mp getGeometry] { if {[$g getTechLayer] eq $L} { set onl 1 } } }
      if {!$onl} continue
      set r [$it getBBox]
      foreach once 1 { foreach once2 1 {
        # overlap or abutment
        if {[$b xMin] > [$r xMax] || [$b xMax] < [$r xMin] || [$b yMin] > [$r yMax] || [$b yMax] < [$r yMin]} continue
        set bx [expr {([$b xMin] + [$b xMax]) / 2}]; set by [expr {([$b yMin] + [$b yMax]) / 2}]
        set mx [expr {([$r xMin] + [$r xMax]) / 2}]; set my [expr {([$r yMin] + [$r yMax]) / 2}]
        # one straight segment on the common centre line: the two boxes share their x range (vertical) or y range (horizontal)
        set ox0 [expr {max([$b xMin], [$r xMin])}]; set ox1 [expr {min([$b xMax], [$r xMax])}]
        set oy0 [expr {max([$b yMin], [$r yMin])}]; set oy1 [expr {min([$b yMax], [$r yMax])}]
        if {$ox1 - $ox0 >= [$L getWidth]} { set x [expr {($ox0 + $ox1) / 2}]; set p0 [list $x $by]; set p1 [list $x $my]
        } elseif {$oy1 - $oy0 >= [$L getWidth]} { set y [expr {($oy0 + $oy1) / 2}]; set p0 [list $bx $y]; set p1 [list $mx $y]
        } else continue
        if {$p0 eq $p1} { set p1 [list [lindex $p0 0] [expr {[lindex $p0 1] + [$L getWidth]}]] }
        set w [odb::dbWire_create $net]
        set e [odb::dbWireEncoder]
        $e begin $w; $e newPath $L ROUTED
        $e addPoint [lindex $p0 0] [lindex $p0 1]; $e addPoint [lindex $p1 0] [lindex $p1 1]
        $e end
        set done 1; incr n
      } }
    } }
    if {!$done} { incr skip }
  }
  puts "OT_PAD_ABUT_WIRE $n macro_pin pad nets got their pin-to-pin wire segment ($skip one-pad block-pin nets without a common pin layer left alone)"
}
if {[catch {paw::run} e]} { puts "OT_PAD_ABUT_WIRE ERROR: $e"; error "OT_PAD_ABUT_WIRE: $e" }
