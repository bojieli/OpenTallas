# PRE_DETAIL_PLACE extra hook (NATIVE-FIX3/gl4, 2026-10-18; spec "pre_dpl_extra", sourced by the kit pre_dpl.tcl AFTER
# out_flop_release.tcl): PIN CHAIN PULL.  Every port whose pin flop sits at its pin (io_flop_at_pins.tcl) also gets the
# single-fanout INV / BUF / HB cells between the pin and that flop (the synthesis QN inverter, the ORFS port buffer, the
# GPL / resizer repair buffers) placed on the pin -> flop segment, so detailed placement legalises them beside the face.
#
# Why (NATIVE-3 audit, claude/native-3-1017 73adc87ea, dsdv_gunit_l4-g3-30d12242b): io_flop_at_pins.tcl fixes the FLOPS
# only.  The chain cells start at the core centre (global_place -force_center_initial_place; the port buffers are made
# after the PRE_GLOBAL_PLACE hook) and the FIRM 4-column pin-flop band along the N face pushed a few of them 100-150 um
# sideways: rn_o[122] flop at x 158.9 beside its pin (158.7) but QN -> BUF 158 -> INV 40.8 -> BUF 43 -> port BUF 85 ->
# pin 158.7 (launch 236.3 ps), rn_i[215] pin 140.5 -> port BUF 287 -> BUF 269 -> flop 142 (capture 197.8).  Placement
# only, 0 cycles, function unchanged.
#   OT_CHAIN_PULL_UM (default 6.0)  a chain cell further than this from its target point is moved
#   OT_CHAIN_PULL_HOPS (default 8)  cells walked between a port and its flop
#   OT_CHAIN_PULL_RE                only ports whose name matches (default: every signal port)
set cp_blk [ord::get_db_block]
set cp_dbu [[$cp_blk getTech] getDbUnitsPerMicron]
set cp_core [$cp_blk getCoreArea]
set cp_thr [expr {[info exists ::env(OT_CHAIN_PULL_UM)] && $::env(OT_CHAIN_PULL_UM) ne "" ? double($::env(OT_CHAIN_PULL_UM)) : 6.0}]
set cp_hops [expr {[info exists ::env(OT_CHAIN_PULL_HOPS)] && $::env(OT_CHAIN_PULL_HOPS) ne "" ? $::env(OT_CHAIN_PULL_HOPS) : 8}]
set cp_re [expr {[info exists ::env(OT_CHAIN_PULL_RE)] ? $::env(OT_CHAIN_PULL_RE) : ""}]
set cp_ports 0; set cp_moved 0; set cp_nochain 0; set cp_noff 0; set cp_max 0.0; set cp_list {}
foreach bt [$cp_blk getBTerms] {
  set io [$bt getIoType]
  if {$io ne "INPUT" && $io ne "OUTPUT"} continue
  if {$cp_re ne "" && ![regexp -- $cp_re [$bt getName]]} continue
  set net [$bt getNet]
  if {$net eq "NULL" || $net eq ""} continue
  if {[$net getSigType] ne "SIGNAL"} continue
  # walk the single-fanout chain from the pin to its flop; chain = cells from the pin side
  set chain {}; set ff ""; set cn $net
  for {set hop 0} {$hop < $cp_hops} {incr hop} {
    set loads {}; set drv ""
    foreach it [$cn getITerms] {
      if {[$it isOutputSignal]} { set drv $it } elseif {[$it isInputSignal]} { lappend loads $it }
    }
    if {$io eq "OUTPUT"} {
      # the net feeds only the next chain cell (or, on the port net, only the port)
      if {[llength $loads] != ($hop == 0 ? 0 : 1) || $drv eq ""} break
      set ci [$drv getInst]
    } else {
      if {[llength $loads] != 1 || ($hop > 0 && $drv eq "")} break
      set ci [[lindex $loads 0] getInst]
    }
    set cm [[$ci getMaster] getName]
    if {[string match "DFF*" $cm] || [string match "ASYNC_DFF*" $cm]} {
      if {$io eq "INPUT" && [[[lindex $loads 0] getMTerm] getName] ne "D"} break
      set ff $ci; break
    }
    if {![regexp {^(BUF|INV|HB)} $cm]} break
    lappend chain $ci
    set nx ""
    foreach it [$ci getITerms] {
      if {[[$it getMTerm] getSigType] ne "SIGNAL"} continue
      if {$io eq "OUTPUT" ? [$it isInputSignal] : [$it isOutputSignal]} { set nx [$it getNet] }
    }
    if {$nx eq "" || $nx eq "NULL"} break
    set cn $nx
  }
  if {$ff eq ""} { incr cp_noff; continue }
  if {![llength $chain]} { incr cp_nochain; continue }
  incr cp_ports
  set bb [$bt getBBox]
  set px [expr {double([$bb xMin] + [$bb xMax]) / 2.0}]; set py [expr {double([$bb yMin] + [$bb yMax]) / 2.0}]
  set fb [$ff getBBox]
  set fx [expr {double([$fb xMin] + [$fb xMax]) / 2.0}]; set fy [expr {double([$fb yMin] + [$fb yMax]) / 2.0}]
  set n [llength $chain]; set k 0
  foreach ci $chain {
    incr k
    if {[$ci getPlacementStatus] in {FIRM LOCKED FIXED COVER}} continue
    set tx [expr {$px + ($fx - $px) * $k / ($n + 1.0)}]; set ty [expr {$py + ($fy - $py) * $k / ($n + 1.0)}]
    set cb [$ci getBBox]
    set cx [expr {double([$cb xMin] + [$cb xMax]) / 2.0}]; set cy [expr {double([$cb yMin] + [$cb yMax]) / 2.0}]
    set d [expr {(abs($cx - $tx) + abs($cy - $ty)) / $cp_dbu}]
    if {$d <= $cp_thr} continue
    set w [[$ci getMaster] getWidth]; set h [[$ci getMaster] getHeight]
    set x [expr {max([$cp_core xMin], min(round($tx - $w / 2.0), [$cp_core xMax] - $w))}]
    set y [expr {max([$cp_core yMin], min(round($ty - $h / 2.0), [$cp_core yMax] - $h))}]
    $ci setLocation $x $y
    $ci setPlacementStatus PLACED
    incr cp_moved
    if {$d > $cp_max} { set cp_max $d }
    lappend cp_list [list $d [$bt getName] [$ci getName]]
  }
}
puts [format "OT_CHAIN_PULL: %d ports with a pin-flop chain, %d chain cells moved onto their pin -> flop segment (max %.1f um), %d ports without a chain cell, %d without a single pin flop" \
        $cp_ports $cp_moved $cp_max $cp_nochain $cp_noff]
foreach e [lrange [lsort -real -decreasing -index 0 $cp_list] 0 19] {
  puts [format "OT_CHAIN_PULL   %6.1f um  %s  %s" {*}$e]
}
