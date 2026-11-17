# pg_pin_notch.tcl (PG-PIN-NOTCH-1, FABLE-FIX-S81-SERDES2 2026-11-17): keep die PG stripes off the access of hard-macro signal pins.
# Class (serdes__t13, ot_s81_kp4_dchn; 63 of the 607 residual detail-route violations):
#  (a) pin face: cw_q[544] M5 pins, 0.288 pitch, on the macro top edge; the die M5 VSS/VDD pair (pitch 4.32) resumes 0.096 um above
#      the edge, so every 15th pin runs up beside (touching) the VDD stripe: 36 shorts + 21 EOL keep-out.
#  (b) interior pin: clk / rst_n M5 pins in the middle of the macro lie under the die M6 VSS/VDD pair that crosses the macro; the only
#      access is an M6 stub in the 96-nm pair gap: 4 + 2 metal-spacing violations.
# Form (PG ECO before detail route, special wires only): for every signal pin shape P of a block instance, on routing layer Lp,
#  (a) a PG stripe on Lp that runs along P's direction, within OT_PG_PIN_NOTCH_SIDE (0.084 um) beside P's track and within
#      OT_PG_PIN_NOTCH_NEAR (0.3 um) of P lengthwise, loses the part within OT_PG_PIN_NOTCH_LEN (0.65 um) of P;
#  (b) when P does not touch the instance boundary, a PG stripe on the next routing layer that crosses over P loses the part within
#      OT_PG_PIN_NOTCH_OVER (1.0 um) of P.
# PG vias that land on the notched layer and sit inside a removed part are removed with it; vias of other layers are kept.  Every stripe keeps its other
# crossings, so the grid stays connected through the remaining straps.  No signal net, cell, pin or guide changes.
# New kits should get the same geometry from the PDN (macro halo on pin faces / macro phase against the M6 pair): this hook then
# finds nothing.  OT_PG_PIN_NOTCH=0 turns it off.
namespace eval ppn {}
proc ppn::env {n d} { if {[info exists ::env($n)] && $::env($n) ne ""} { return $::env($n) }; return $d }
# cut window list {lo hi} out of the span [a, b): returns the remaining pieces
proc ppn::cut {a b wins} {
  set pieces [list [list $a $b]]
  foreach w $wins { lassign $w lo hi; set nxt {}
    foreach p $pieces { lassign $p pa pb
      if {$hi <= $pa || $lo >= $pb} { lappend nxt $p; continue }
      if {$lo > $pa} { lappend nxt [list $pa $lo] }
      if {$hi < $pb} { lappend nxt [list $hi $pb] } }
    set pieces $nxt }
  return $pieces
}
# 1 when via box v has layer L as its bottom or top routing layer
proc ppn::via_on {v L} {
  foreach get {getTechVia getBlockVia} {
    set o [$v $get]; if {$o eq "NULL" || $o eq ""} continue
    foreach side {getBottomLayer getTopLayer} { if {![catch {$o $side} l] && $l ne "NULL" && [$l getName] eq [$L getName]} { return 1 } }
  }
  return 0
}
proc ppn::run {} {
  if {[ppn::env OT_PG_PIN_NOTCH 1] eq "0"} { puts "OT_PG_PIN_NOTCH off"; return }
  set blk [ord::get_db_block]; set tech [ord::get_db_tech]; set dbu [$blk getDbUnitsPerMicron]
  set side [expr {int(round([ppn::env OT_PG_PIN_NOTCH_SIDE 0.084] * $dbu))}]; set near [expr {int(round([ppn::env OT_PG_PIN_NOTCH_NEAR 0.3] * $dbu))}]
  set len [expr {int(round([ppn::env OT_PG_PIN_NOTCH_LEN 0.65] * $dbu))}]; set over [expr {int(round([ppn::env OT_PG_PIN_NOTCH_OVER 1.0] * $dbu))}]
  # signal pin shapes of block instances: {layer level horiz x0 y0 x1 y1 interior}
  set pins {}
  foreach i [$blk getInsts] {
    if {![[$i getMaster] isBlock]} continue
    set ib [$i getBBox]
    foreach it [$i getITerms] {
      if {![$it isInputSignal] && ![$it isOutputSignal]} continue
      if {[$it getNet] eq "NULL"} continue
      set pb [$it getBBox]; set L ""
      foreach mp [[$it getMTerm] getMPins] { foreach g [$mp getGeometry] { set tl [$g getTechLayer]; if {$tl ne "NULL" && [$tl getType] eq "ROUTING"} { set L $tl } } }
      if {$L eq ""} continue
      set inter [expr {[$pb xMin] > [$ib xMin] && [$pb xMax] < [$ib xMax] && [$pb yMin] > [$ib yMin] && [$pb yMax] < [$ib yMax]}]
      lappend pins [list [$L getRoutingLevel] [$pb xMin] [$pb yMin] [$pb xMax] [$pb yMax] $inter]
    }
  }
  # windows per PG stripe box
  set nbox 0; set nvia 0; set npin 0; array set used {}
  foreach net [$blk getNets] {
    if {![$net isSpecial]} continue
    set st [$net getSigType]; if {$st ne "POWER" && $st ne "GROUND"} continue
    foreach sw [$net getSWires] {
      set cuts {}
      set boxes [$sw getWires]
      foreach sb $boxes {
        if {[$sb isVia]} continue
        set L [$sb getTechLayer]; if {$L eq "NULL" || [$L getType] ne "ROUTING"} continue
        set lv [$L getRoutingLevel]; if {$lv < 4} continue
        set x0 [$sb xMin]; set y0 [$sb yMin]; set x1 [$sb xMax]; set y1 [$sb yMax]
        set vert [expr {($y1 - $y0) > ($x1 - $x0)}]
        set wins {}
        foreach p $pins { lassign $p plv px0 py0 px1 py1 inter
          if {$plv == $lv} {
            # (a) stripe beside the pin, same direction
            if {$vert} { if {$px1 + $side <= $x0 || $px0 - $side >= $x1 || $py1 + $near < $y0 || $py0 - $near > $y1} continue
                         lappend wins [list [expr {$py0 - $len}] [expr {$py1 + $len}]] } \
            else       { if {$py1 + $side <= $y0 || $py0 - $side >= $y1 || $px1 + $near < $x0 || $px0 - $near > $x1} continue
                         lappend wins [list [expr {$px0 - $len}] [expr {$px1 + $len}]] }
            set used($p) 1
          } elseif {$plv + 1 == $lv && $inter} {
            # (b) stripe of the next layer crossing over an interior pin
            if {$vert} { if {$px1 <= $x0 || $px0 >= $x1 || $py1 < $y0 || $py0 > $y1} continue
                         lappend wins [list [expr {$py0 - $over}] [expr {$py1 + $over}]] } \
            else       { if {$py1 <= $y0 || $py0 >= $y1 || $px1 < $x0 || $px0 > $x1} continue
                         lappend wins [list [expr {$px0 - $over}] [expr {$px1 + $over}]] }
            set used($p) 1
          }
        }
        if {![llength $wins]} continue
        lappend cuts [list $sb $L $vert $x0 $y0 $x1 $y1 $wins]
      }
      foreach c $cuts { lassign $c sb L vert x0 y0 x1 y1 wins
        set shape [$sb getWireShapeType]
        set pieces [expr {$vert ? [ppn::cut $y0 $y1 $wins] : [ppn::cut $x0 $x1 $wins]}]
        # PG vias that land on THIS stripe layer and whose centre lies in a removed part go with it.  A via of other layers that
        # merely overlaps the stripe box (e.g. the M1-M2 via row of a std rail under an M6 strap) is never touched.
        foreach v $boxes {
          if {![$v isVia] || [info exists gone($v)]} continue
          if {[$v xMin] >= $x1 || [$v xMax] <= $x0 || [$v yMin] >= $y1 || [$v yMax] <= $y0} continue
          if {![ppn::via_on $v $L]} continue
          set c [expr {$vert ? ([$v yMin] + [$v yMax]) / 2 : ([$v xMin] + [$v xMax]) / 2}]; set keep 0
          foreach p $pieces { lassign $p pa pb; if {$c >= $pa && $c < $pb} { set keep 1 } }
          if {!$keep} { set gone($v) 1; odb::dbSBox_destroy $v; incr nvia }
        }
        odb::dbSBox_destroy $sb
        foreach p $pieces { lassign $p pa pb; if {$pb - $pa < 2 * [$L getWidth]} continue
          if {$vert} { odb::dbSBox_create $sw $L $x0 $pa $x1 $pb $shape } else { odb::dbSBox_create $sw $L $pa $y0 $pb $y1 $shape } }
        incr nbox
      }
    }
  }
  puts "OT_PG_PIN_NOTCH [llength $pins] block signal pins, [array size used] with a PG stripe at their access; $nbox stripe boxes notched, $nvia PG vias removed"
}
if {[catch {ppn::run} e]} { puts "OT_PG_PIN_NOTCH ERROR: $e"; error "OT_PG_PIN_NOTCH: $e" }
