# pad_in_direct.tcl (PAD-IN-DIRECT-1, FABLE-FIX-S81-SERDES2 2026-11-17): macro_pin INPUT pads keep their direct net.
# Class: a die INPUT pin placed on a hard-macro pin (io.tcl "on the macro pin", e.g. S81 io_pma_rx[543:0] on ot_s81_pma_rxm pma_rx)
# is one piece of metal with that macro pin.  pad_bump_dt.tcl protected only the OUTPUT pads (S81-PMATX-DT), so buffer_ports put an
# input buffer between the port and the macro pin: the die pin then lies on the macro pin of a DIFFERENT net and detail route ends
# with one M5 short per bit (serdes__t13: 544 of the 607 residual violations).
# Form (ECO on a placed / globally routed DB, before detail route): for every INPUT BTerm whose pin box overlaps, on the same layer,
# the pin of a block instance reached through a chain of single-fanout buffers only (port buffer, max-wire repeaters; each net has
# one sink), the block pin is reconnected to the port net, the chain buffers and their nets are removed, the port net is
# dont_touch and gets the single-gcell guide stack the direct output pads have (M2..pin layer).  Same ports, macros and logic.
# New kits: gen_phys marks these nets dont_touch before buffer_ports, then this hook finds nothing.  OT_PAD_IN_DIRECT=0 turns it off.
namespace eval pid {}
proc pid::run {} {
  if {[info exists ::env(OT_PAD_IN_DIRECT)] && $::env(OT_PAD_IN_DIRECT) eq "0"} { puts "OT_PAD_IN_DIRECT off"; return }
  set blk [ord::get_db_block]; set tech [ord::get_db_tech]
  set gc [expr {int(round(([info exists ::env(OT_PG_ROW_GUIDES_GCELL_UM)] ? $::env(OT_PG_ROW_GUIDES_GCELL_UM) : 0.57) * [$blk getDbUnitsPerMicron]))}]
  set n 0; set seen 0; set nb 0
  foreach bt [$blk getBTerms] {
    if {[$bt getIoType] ne "INPUT" || [$bt getSigType] ne "SIGNAL"} continue
    set net [$bt getNet]; if {$net eq "NULL"} continue
    # walk the single-fanout buffer chain from the port (port buffer, max-wire repeaters) to the first non-buffer sink
    set bufs {}; set nets {}; set cur $net; set mt ""
    for {set d 0} {$d < 16} {incr d} {
      set sinks {}; foreach t [$cur getITerms] { if {[$t isInputSignal]} { lappend sinks $t } }
      if {[llength $sinks] != 1 || ($d > 0 && [llength [$cur getBTerms]])} break
      set t [lindex $sinks 0]; set i [$t getInst]
      if {[[$i getMaster] isBlock]} { set mt $t; break }
      if {![string match "BUF*" [[$i getMaster] getName]]} break
      set on ""; foreach o [$i getITerms] { if {[$o isOutputSignal]} { set on [$o getNet] } }
      if {$on eq "" || $on eq "NULL"} break
      lappend bufs $i; lappend nets $on; set cur $on
    }
    if {$mt eq "" || ![llength $bufs]} continue
    # the die pin box must lie on the macro pin (same layer)
    set hit ""; set mb [$mt getBBox]
    foreach bp [$bt getBPins] { foreach b [$bp getBoxes] {
      if {[$b xMin] < [$mb xMax] && [$b xMax] > [$mb xMin] && [$b yMin] <= [$mb yMax] && [$b yMax] >= [$mb yMin]} { set hit $b } } }
    if {$hit eq ""} continue
    incr seen
    $net setDoNotTouch 0
    foreach i $bufs { $i setDoNotTouch 0 }; foreach o $nets { $o setDoNotTouch 0 }
    $mt disconnect; $mt connect $net
    foreach g [$net getGuides] { odb::dbGuide_destroy $g }
    foreach i $bufs { odb::dbInst_destroy $i }
    foreach o $nets { odb::dbNet_destroy $o }
    incr nb [llength $bufs]
    set gx [expr {(([$hit xMin] + [$hit xMax]) / 2) / $gc * $gc}]; set gy [expr {(([$hit yMin] + [$hit yMax]) / 2) / $gc * $gc}]
    set top [[$hit getTechLayer] getRoutingLevel]
    for {set lv 2} {$lv <= $top} {incr lv} {
      set L [$tech findRoutingLayer $lv]
      odb::dbGuide_create $net $L $L [odb::new_Rect $gx $gy [expr {$gx + $gc}] [expr {$gy + $gc}]] 0
    }
    $net setDoNotTouch 1
    incr n
  }
  puts "OT_PAD_IN_DIRECT $n macro_pin input pads reconnected to their macro pin ($nb buffers and their nets removed)"
}
if {[catch {pid::run} e]} { puts "OT_PAD_IN_DIRECT ERROR: $e"; error "OT_PAD_IN_DIRECT: $e" }
