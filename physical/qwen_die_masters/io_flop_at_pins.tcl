# PRE_GLOBAL_PLACE hook (drive-0849, 2026-10-09): out_flop_at_pins.tcl extended to INPUT ports.  For every output port its
# launching flop, and for every input port its single capturing flop (the port net -- through up to three single-fanout
# INV / BUF stages -- reaches exactly one DFF D pin), is placed FIRM just inside the core on the pin's own edge, in up to
# 4 staggered columns by pin order.  Why: low-utilisation die-slot outlines (qfd_sp_constants_sequencer_sys 777.6 x 1000
# at ~1 %, qfd_sp_res_ser) let timing-driven GPL pull pin flops into the central logic, so pin -> flop and flop -> pin
# become 200-760 ps wires (ICUT 155370387: vm_rq -> line -514.8, c_data -309; res_ser r2q: i_addr -> c_addr 535 ps wire).
# The pin flop then carries the distance on a reg -> reg path with a full cycle.  out_flop_release.tcl (PRE_DETAIL_PLACE)
# returns them to PLACED for DPL (same list file).  Placement only, 0 cycles.
set ot_blk [ord::get_db_block]
set ot_dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set ot_core [$ot_blk getCoreArea]
set cx0 [expr {double([$ot_core xMin]) / $ot_dbu}]; set cx1 [expr {double([$ot_core xMax]) / $ot_dbu}]
set cy0 [expr {double([$ot_core yMin]) / $ot_dbu}]; set cy1 [expr {double([$ot_core yMax]) / $ot_dbu}]
set ot_die [$ot_blk getDieArea]
set dx0 [expr {double([$ot_die xMin]) / $ot_dbu}]; set dx1 [expr {double([$ot_die xMax]) / $ot_dbu}]
set dy0 [expr {double([$ot_die yMin]) / $ot_dbu}]; set dy1 [expr {double([$ot_die yMax]) / $ot_dbu}]
set ot_gap [expr {[info exists ::env(OT_OFLOP_GAP)] ? $::env(OT_OFLOP_GAP) : 1.0}]
proc ot_of_drv {net} {
  foreach it [$net getITerms] { if {[$it isOutputSignal]} { return $it } }
  return ""
}
# ds-1010 2026-10-11: the chain net may also feed the flop's OWN hold / enable mux (a DFFE maps to DFF + mux whose feedback
# can tap the Q-polarity net after the output inverter): accept a net whose only other loads are cells whose output is the
# candidate flop's D net (lane lcrpx: 556 li_d / flt output flops skipped, li_d 240 ps of wire, TT -43 / -67).
proc ot_of_fbonly {net cand chain} {
  if {![ot_of_isff $cand]} { return 0 }
  set dnet ""
  foreach it [$cand getITerms] { if {[[$it getMTerm] getName] eq "D"} { set dnet [$it getNet] } }
  if {$dnet eq "" || $dnet eq "NULL"} { return 0 }
  foreach it [$net getITerms] {
    if {![$it isInputSignal]} continue
    set li [$it getInst]
    if {$li eq $chain} continue
    set ok 0
    foreach ot [$li getITerms] { if {[$ot isOutputSignal] && [$ot getNet] eq $dnet} { set ok 1 } }
    if {!$ok} { return 0 }
  }
  return 1
}
proc ot_of_isff {inst} { return [string match "DFF*" [[$inst getMaster] getName]] }
proc ot_of_isbuf {inst} { set m [[$inst getMaster] getName]; return [expr {[string match "INV*" $m] || [string match "BUF*" $m]}] }
# the single input-signal sink of a net (or "" if 0 or > 1 sinks)
proc ot_of_sink {net} {
  set s ""
  foreach it [$net getITerms] {
    if {![$it isInputSignal]} continue
    if {$s ne ""} { return "" }
    set s $it
  }
  return $s
}
set ot_list {}; set ot_n 0; set ot_ni 0; set ot_skip 0
set cand {}
set ot_seen [dict create]
# OT_OFLOP_PORT_RE (ds-1010 2026-10-10, optional): anchor only the ports whose name matches this regexp (default: all).
# coll lane LCR: anchoring the 1,027 link-side rx/tx gearbox flops as well stretched the endpoint's seq/fill logic across
# the tile (lcrpe -560 exp_seq -> fill); only the new core-face credit links (li_* / lo_*) need anchoring there.
set ot_port_re [expr {[info exists ::env(OT_OFLOP_PORT_RE)] ? $::env(OT_OFLOP_PORT_RE) : {}}]
foreach bt [$ot_blk getBTerms] {
  set io [$bt getIoType]
  if {$ot_port_re ne "" && ![regexp -- $ot_port_re [$bt getName]]} continue
  set net [$bt getNet]; if {$net eq "NULL"} continue
  set ff ""
  if {$io eq "OUTPUT"} {
    set d [ot_of_drv $net]; if {$d eq ""} { incr ot_skip; continue }
    set inst [$d getInst]
    for {set hop 0} {$hop < 4} {incr hop} {
      if {[ot_of_isff $inst]} { set ff $inst; break }
      if {![ot_of_isbuf $inst]} break
      set nxt ""
      foreach it [$inst getITerms] {
        if {![$it isInputSignal]} continue
        set n2 [$it getNet]; if {$n2 eq "NULL"} continue
        set d2 [ot_of_drv $n2]
        if {$d2 ne "" && ([llength [$n2 getITerms]] == 2 || [ot_of_fbonly $n2 [$d2 getInst] $inst])} { set nxt [$d2 getInst] }
      }
      if {$nxt eq ""} break
      set inst $nxt
    }
  } elseif {$io eq "INPUT"} {
    if {[$net getSigType] eq "CLOCK"} continue
    set s [ot_of_sink $net]; if {$s eq ""} { incr ot_skip; continue }
    for {set hop 0} {$hop < 4} {incr hop} {
      set inst [$s getInst]
      if {[ot_of_isff $inst]} {
        if {[[$s getMTerm] getName] eq "D"} { set ff $inst }
        break
      }
      if {![ot_of_isbuf $inst]} break
      set on ""
      foreach it [$inst getITerms] { if {[$it isOutputSignal]} { set on [$it getNet] } }
      if {$on eq "" || $on eq "NULL"} break
      set s [ot_of_sink $on]; if {$s eq ""} break
    }
  } else { continue }
  if {$ff eq ""} { incr ot_skip; continue }
  set fn [$ff getName]
  if {[dict exists $ot_seen $fn]} continue
  dict set ot_seen $fn 1
  set bb [$bt getBBox]
  set px [expr {double([$bb xMin] + [$bb xMax]) / 2.0 / $ot_dbu}]
  set py [expr {double([$bb yMin] + [$bb yMax]) / 2.0 / $ot_dbu}]
  # ds-1010 2026-10-10: the side is the NEAREST DIE EDGE.  The old test compared against the core box, so a block whose
  # core touches the die on the left/right (core-area 0 0.54 W H-0.54: every S81 coll tile, the lane tile) classified
  # its W/E-face pins (centre x 0.012 > cx0 0) as T: their flops were stacked along the top edge at the pin's x
  # (coll_cb crpa: u_lo0 l_data[55] FIRM at (0.1, 338.4) for wlo_d[55] at (0, 155.7) -> 730 ps of wire, TT -577).
  set dl [expr {$px - $dx0}]; set dr [expr {$dx1 - $px}]; set dbo [expr {$py - $dy0}]; set dt [expr {$dy1 - $py}]
  set dm [expr {min($dl, $dr, $dbo, $dt)}]
  if {$dl == $dm} { set side L } elseif {$dr == $dm} { set side R } elseif {$dbo == $dm} { set side B } else { set side T }
  lappend cand [list $side [expr {($side eq "L" || $side eq "R") ? $py : $px}] $ff $px $py $io]
}
foreach side {L R B T} { set ot_k($side) 0 }
foreach c [lsort -real -index 1 $cand] {
  lassign $c side pos ff px py io
  set col [expr {$ot_k($side) % 4}]; incr ot_k($side)
  set w [expr {double([[$ff getMaster] getWidth]) / $ot_dbu}]
  set h [expr {double([[$ff getMaster] getHeight]) / $ot_dbu}]
  switch $side {
    L { set x [expr {$cx0 + $ot_gap + $col * ($w + 0.2)}]; set y $py }
    R { set x [expr {$cx1 - $ot_gap - ($col + 1) * ($w + 0.2)}]; set y $py }
    B { set x $px; set y [expr {$cy0 + $ot_gap + $col * $h}] }
    T { set x $px; set y [expr {$cy1 - $ot_gap - ($col + 1) * $h}] }
  }
  $ff setLocation [expr {round($x * $ot_dbu)}] [expr {round($y * $ot_dbu)}]
  $ff setPlacementStatus FIRM
  lappend ot_list [$ff getName]
  if {$io eq "INPUT"} { incr ot_ni } else { incr ot_n }
}
set fh [open $::env(RESULTS_DIR)/ot_out_flop_at_pins.txt w]
foreach n $ot_list { puts $fh $n }
close $fh
puts "OT_IOFLOP fixed $ot_n output-port and $ot_ni input-port flops at their pins ($ot_skip ports not single-flop)"
if {$ot_n + $ot_ni == 0} { error "OT_IOFLOP: no pin flop found (netlist changed?)" }
