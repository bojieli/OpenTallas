# pad_abut_strip.tcl (PAD-ABUT-STRIP-1, S81-FIX-OPUS 2026-11-17): PRE_FINAL_REPORT partner of pad_abut_wire.tcl.
# pad_abut_wire.tcl gives each macro_pin pad net (one BTerm + one block-instance ITerm whose pin boxes overlap/abut on one
# routing layer) one segment inside the two pin shapes so the ORFS route stage's routed check passes.  OpenRCX then stops
# in final_report on that same metal: "[ERROR ODB-0420] tmg_conn::detachTilePins: tilepin inside iterm" (serdes__t13 H17
# r3: DRC 0, antenna 0, 5_2_route + 6_1_fill written, 6_report exit).  The segment carries no parasitic (the pins abut), so
# before extraction it is removed again: every net of that class whose wire lies entirely inside the union of its BTerm
# pin boxes and its ITerm box loses the wire.  Any other net is untouched.  OT_PAD_ABUT_STRIP=0 turns it off.
namespace eval pas {}
proc pas::inside {x y boxes} {
  foreach b $boxes { if {$x >= [lindex $b 0] && $x <= [lindex $b 2] && $y >= [lindex $b 1] && $y <= [lindex $b 3]} { return 1 } }
  return 0
}
proc pas::run {} {
  if {[info exists ::env(OT_PAD_ABUT_STRIP)] && $::env(OT_PAD_ABUT_STRIP) eq "0"} { puts "OT_PAD_ABUT_STRIP off"; return }
  set blk [ord::get_db_block]; set n 0; set kept 0
  # walk the die pins (a pad net has exactly one BTerm), not every net of the block
  foreach bt [$blk getBTerms] {
    set net [$bt getNet]; if {$net eq "NULL" || [$net isSpecial]} continue
    set w [$net getWire]; if {$w eq "NULL"} continue
    set bts [$net getBTerms]; set its [$net getITerms]
    if {[llength $bts] != 1 || [llength $its] != 1} continue
    set it [lindex $its 0]; if {![[[$it getInst] getMaster] isBlock]} continue
    set boxes {}
    foreach bp [[lindex $bts 0] getBPins] { foreach b [$bp getBoxes] { lappend boxes [list [$b xMin] [$b yMin] [$b xMax] [$b yMax]] } }
    set r [$it getBBox]; lappend boxes [list [$r xMin] [$r yMin] [$r xMax] [$r yMax]]
    set ok 1; set npts 0
    set dec [odb::dbWireDecoder]; $dec begin $w
    for {set guard 0} {$guard < 100000} {incr guard} {
      set op [$dec next]
      if {$op == $odb::dbWireDecoder_END_DECODE} break
      if {$op in [list $odb::dbWireDecoder_POINT $odb::dbWireDecoder_POINT_EXT $odb::dbWireDecoder_JUNCTION]} {
        set p [$dec getPoint]; incr npts
        if {![pas::inside [lindex $p 0] [lindex $p 1] $boxes]} { set ok 0; break }
      } elseif {$op in [list $odb::dbWireDecoder_VIA $odb::dbWireDecoder_TECH_VIA]} { set ok 0; break }
    }
    if {!$ok || $npts == 0} { incr kept; continue }
    odb::dbWire_destroy $w; incr n
  }
  puts "OT_PAD_ABUT_STRIP $n in-pin pad segments removed before extraction ($kept one-pad block-pin nets with real routing kept)"
}
if {[catch {pas::run} e]} { puts "OT_PAD_ABUT_STRIP ERROR: $e"; error "OT_PAD_ABUT_STRIP: $e" }
