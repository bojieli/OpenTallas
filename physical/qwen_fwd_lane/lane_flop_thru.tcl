# PRE_GLOBAL_PLACE hook (RLYH0-FIN 2026-10-19): io_flop_at_pins.tcl, then every PASS-THROUGH pin flop -- D from an input
# port, Q to an output port (a lane station: one flop per bit, a[i] -> FF -> b[i]) -- is moved from the input face onto the
# L path between its two pins, at fraction OT_IOFLOP_THRU_FRAC of the path from the input pin (0.5 = the middle).
# Why: io_flop_at_pins anchors such a flop at the face it meets first (the input), so its whole a -> b distance lands on
# the launch side.  On the 600-b lane frames the die-assigned faces are perpendicular (NE: a on N, b on E; EN: a on E, b on N)
# and the pin pairs are up to 153 um apart: native launch 261.6 ps (NE, b[482]) / 231.4 ps (EN, b[389]) > 220 while the
# capture side used 74-77 of its 190.  Splitting the wire balances the two budgets.  Placement only, 0 cycles, same RTL,
# same pins; the flops stay FIRM through global placement and out_flop_release.tcl (same list file) hands them to DPL.
# Ports whose flop is not a single pass-through register keep the io_flop_at_pins anchor.
set ot_thru_src /src/physical/qwen_die_masters/io_flop_at_pins.tcl
if {![file exists $ot_thru_src] && [info script] ne ""} {
  set ot_thru_src [file join [file dirname [info script]] .. qwen_die_masters io_flop_at_pins.tcl]
}
source $ot_thru_src
set ot_thru_f [expr {[info exists ::env(OT_IOFLOP_THRU_FRAC)] && $::env(OT_IOFLOP_THRU_FRAC) ne "" ? double($::env(OT_IOFLOP_THRU_FRAC)) : 0.5}]
if {$ot_thru_f < 0.0 || $ot_thru_f > 1.0} { error "OT_IOFLOP_THRU: OT_IOFLOP_THRU_FRAC $ot_thru_f outside 0..1" }
# the port BTerm reached from a net through <= 3 single-sink BUF / INV (forward: Q -> output port)
proc ot_thru_out_port {net} {
  for {set hop 0} {$hop < 4} {incr hop} {
    if {$net eq "" || $net eq "NULL"} { return "" }
    set bts [$net getBTerms]
    foreach bt $bts { if {[$bt getIoType] eq "OUTPUT"} { return $bt } }
    set s [ot_of_sink $net]; if {$s eq ""} { return "" }
    set inst [$s getInst]
    if {![ot_of_isbuf $inst]} { return "" }
    set nn ""
    foreach it [$inst getITerms] { if {[$it isOutputSignal]} { set nn [$it getNet] } }
    set net $nn
  }
  return ""
}
# the input port BTerm reached backwards from a net through <= 3 BUF / INV (D <- input port)
proc ot_thru_in_port {net} {
  for {set hop 0} {$hop < 4} {incr hop} {
    if {$net eq "" || $net eq "NULL"} { return "" }
    foreach bt [$net getBTerms] { if {[$bt getIoType] eq "INPUT"} { return $bt } }
    set d [ot_of_drv $net]; if {$d eq ""} { return "" }
    set inst [$d getInst]
    if {![ot_of_isbuf $inst]} { return "" }
    set nn ""
    foreach it [$inst getITerms] { if {[$it isInputSignal]} { set nn [$it getNet] } }
    set net $nn
  }
  return ""
}
proc ot_thru_ctr {bt dbu} {
  set bb [$bt getBBox]
  return [list [expr {double([$bb xMin] + [$bb xMax]) / 2.0 / $dbu}] [expr {double([$bb yMin] + [$bb yMax]) / 2.0 / $dbu}]]
}
set ot_thru_n 0; set ot_thru_max 0.0; set ot_thru_sum 0.0
foreach ot_thru_name $ot_list {
  set ff [$ot_blk findInst $ot_thru_name]
  if {$ff eq "NULL" || $ff eq ""} continue
  set dn ""; set qn ""
  foreach it [$ff getITerms] {
    set mt [[$it getMTerm] getName]
    if {$mt eq "D"} { set dn [$it getNet] }
    if {$mt eq "Q" || $mt eq "QN"} { set qn [$it getNet] }
  }
  set ib [ot_thru_in_port $dn]; set ob [ot_thru_out_port $qn]
  if {$ib eq "" || $ob eq ""} continue
  lassign [ot_thru_ctr $ib $ot_dbu] ax ay
  lassign [ot_thru_ctr $ob $ot_dbu] bx by
  # L path a -> (ax, by) -> b (the first leg leaves the input face perpendicular to it when a is on N / S; for a W / E
  # input the other corner (bx, ay) does the same)
  set side_ns [expr {min($ay - $dy0, $dy1 - $ay) <= min($ax - $dx0, $dx1 - $ax)}]
  if {$side_ns} { set kx $ax; set ky $by } else { set kx $bx; set ky $ay }
  set l1 [expr {abs($kx - $ax) + abs($ky - $ay)}]; set l2 [expr {abs($bx - $kx) + abs($by - $ky)}]
  set L [expr {$l1 + $l2}]
  set t [expr {$ot_thru_f * $L}]
  if {$L <= 0.0} continue
  if {$t <= $l1} {
    set fx [expr {$l1 > 0 ? $ax + ($kx - $ax) * $t / $l1 : $ax}]; set fy [expr {$l1 > 0 ? $ay + ($ky - $ay) * $t / $l1 : $ay}]
  } else {
    set u [expr {$t - $l1}]
    set fx [expr {$kx + ($bx - $kx) * $u / $l2}]; set fy [expr {$ky + ($by - $ky) * $u / $l2}]
  }
  set w [expr {double([[$ff getMaster] getWidth]) / $ot_dbu}]; set h [expr {double([[$ff getMaster] getHeight]) / $ot_dbu}]
  set fx [expr {min(max($fx - $w / 2.0, $cx0 + 0.5), $cx1 - $w - 0.5)}]
  set fy [expr {min(max($fy - $h / 2.0, $cy0 + 0.5), $cy1 - $h - 0.5)}]
  $ff setPlacementStatus PLACED                                ;# a FIRM origin cannot move (ODB-0359)
  $ff setLocation [expr {round($fx * $ot_dbu)}] [expr {round($fy * $ot_dbu)}]
  $ff setPlacementStatus FIRM
  incr ot_thru_n
  set ot_thru_sum [expr {$ot_thru_sum + $L}]
  if {$L > $ot_thru_max} { set ot_thru_max $L }
}
puts [format "OT_IOFLOP_THRU moved %d pass-through pin flops to %.2f of their a -> b L path (pin pair mean %.1f um, max %.1f um)" \
        $ot_thru_n $ot_thru_f [expr {$ot_thru_n ? $ot_thru_sum / $ot_thru_n : 0.0}] $ot_thru_max]
if {$ot_thru_n == 0} { error "OT_IOFLOP_THRU: no pass-through pin flop found (netlist changed?)" }
