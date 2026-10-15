# PRE_GLOBAL_PLACE hook (drive-0849, 2026-10-09): out_flop_at_pins.tcl extended to INPUT ports.  For every output port its
# launching flop, and for every input port its capturing flops (through bounded INV / BUF branches), are placed FIRM
# just inside the core on the pin's own edge. Historical single-capture anchors use up to
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
# OT_OFLOP_COLS (el1011-ds-coll 2026-10-11, default 4): staggered rows/columns per face.  A face whose boundary flops
# outnumber 4 x (face length / flop width) gets overlapping FIRM sites and DPL pushes the overflow away from the pins
# (coll cb S face: 2,100 t_vm + 592 f_vm flops on 680 um, t_vm[0] 270 ps of wire from its pin, kps TT -65).
set ot_cols [expr {[info exists ::env(OT_OFLOP_COLS)] ? $::env(OT_OFLOP_COLS) : 4}]
# Opt-in knobs (el1013-finishing-recipe 2026-10-13, ref_tile kit recipe 2; unset = the behaviour above, unchanged):
#   OT_OFLOP_HOPS (default 4): cells walked between a port and its flop, the flop included.  With the pin hold stages
#     inserted first by the same hook (leaf_iohold.tcl: flop -> [INV/BUF <= 3] -> BUF -> HB4 -> BUF -> port; leaf_inhold.tcl:
#     port -> HB4 -> BUF -> flop D) the default stops inside the stage and the flop stays unanchored.
#   OT_OFLOP_ALLOW_NONE=1: finding no pin flop is reported, not an error (a default-on hook on a tile whose ports all
#     feed macros / hard children).
# AUTO SPREAD (flowfix 2026-10-13; the same model as tools/pin_fit.py oflop_plan, constants kept equal by
# tools/closure_loop/test_pin_fit.py).  With the pin hold stages of kit recipe 2 FIRM at the pins (leaf_iohold.tcl: BUF +
# HB4 + BUF per output, leaf_inhold.tcl: HB4 + BUF per input) the default gap puts the flops ON the stages: at ~10 b/um
# (2.8 pins per cell row) the legalised stages take x 2.2-6.7, the flops x 3.2-8.3, they interleave and every flop ->
# stage -> pin chain crosses the column behind the face more than once (qkd_seq_fan-kc3 GRT-0116, one track short in 66
# gcells at x 7.98-8.55; s81su swtl / swth / qbtl; closed by hand with OT_OFLOP_GAP 4.5 and 6 columns, kc4).
# Per face, over the densest ot_au_win um: hold depth = FIRM chain-cell width x row height / window.  From ot_au_dense um
# the flops start behind the stages (gap = depth x ot_au_slack) in enough columns for one flop per pin (W / E: 2 x pins
# per row; N / S: 1.5 x pins per flop pitch).  A face without FIRM hold cells, or a sparse one, keeps gap / columns.
#   OT_OFLOP_GAP set: that gap on every face (no derivation).  OT_OFLOP_COLS: the minimum column count.
#   OT_OFLOP_AUTO=0: no derivation at all (gap / columns exactly as given).
set ot_au_on [expr {!([info exists ::env(OT_OFLOP_AUTO)] && $::env(OT_OFLOP_AUTO) eq "0")}]
set ot_au_gap_set [expr {[info exists ::env(OT_OFLOP_GAP)] && $::env(OT_OFLOP_GAP) ne ""}]
set ot_au_win 10.0
set ot_au_row 0.27
set ot_au_dense 2.0
set ot_au_slack 1.28
set ot_au_cols_v 2.0
set ot_au_cols_h 1.5
set ot_au_depth_max 0.45
set ot_hops [expr {[info exists ::env(OT_OFLOP_HOPS)] && $::env(OT_OFLOP_HOPS) ne "" ? $::env(OT_OFLOP_HOPS) : 4}]
set ot_allow_none [expr {[info exists ::env(OT_OFLOP_ALLOW_NONE)] && $::env(OT_OFLOP_ALLOW_NONE) eq "1"}]
# Optional source-bound hard-face audit. The sourced audit must inspect every
# actual boundary endpoint and rehash its registered leaf/view binding. A count
# is produced by that audit, never accepted from a caller-supplied environment
# boolean. Own standard-cell endpoints continue through the ordinary anchoring.
set ot_verified_hard_faces 0
if {[info exists ::env(OT_OFLOP_HARD_FACE_AUDIT)]} {
  source $::env(OT_OFLOP_HARD_FACE_AUDIT)
  if {$ot_verified_hard_faces <= 0} { error "OT_IOFLOP: hard-face audit verified no ports" }
}
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
proc ot_of_isff {inst} {
  set master [[$inst getMaster] getName]
  return [expr {[string match "DFF*" $master] || [string match "ASYNC_DFF*" $master]}]
}
proc ot_of_isbuf {inst} { set m [[$inst getMaster] getName]; return [expr {[string match "INV*" $m] || [string match "BUF*" $m] || [string match "HB*" $m]}] }
# el1011-q-coll 2026-10-11: HB* = the ot_hdly kept hold-delay cells between a pin flop and its port (walked like a buffer)
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
# Enumerate data captures through buffer branches. Reset/clock FF loads are not
# capture endpoints; in particular rst may also be data for a reset synchronizer.
proc ot_of_captures {net remaining seen} {
  if {$remaining <= 0 || $net eq "NULL" || [dict exists $seen [$net getName]]} { return {} }
  dict set seen [$net getName] 1
  set found [dict create]
  foreach it [$net getITerms] {
    if {![$it isInputSignal]} continue
    set inst [$it getInst]
    if {[ot_of_isff $inst]} {
      if {[[$it getMTerm] getName] eq "D"} { dict set found [$inst getName] $inst }
    } elseif {[ot_of_isbuf $inst]} {
      foreach ot [$inst getITerms] {
        if {![$ot isOutputSignal]} continue
        foreach ff [ot_of_captures [$ot getNet] [expr {$remaining - 1}] $seen] {
          dict set found [$ff getName] $ff
        }
      }
    }
  }
  set result {}
  foreach name [lsort [dict keys $found]] { lappend result [dict get $found $name] }
  return $result
}
set ot_extra_ports {}
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
  set ff ""; set hw 0.0
  if {$io eq "OUTPUT"} {
    set d [ot_of_drv $net]; if {$d eq ""} { incr ot_skip; continue }
    set inst [$d getInst]
    for {set hop 0} {$hop < $ot_hops} {incr hop} {
      if {[ot_of_isff $inst]} { set ff $inst; break }
      if {![ot_of_isbuf $inst]} break
      if {[$inst getPlacementStatus] eq "FIRM"} { set hw [expr {$hw + double([[$inst getMaster] getWidth]) / $ot_dbu}] }
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
    lappend ot_extra_ports [list $bt [ot_of_captures $net $ot_hops [dict create]]]
    set s [ot_of_sink $net]; if {$s eq ""} { incr ot_skip; continue }
    for {set hop 0} {$hop < $ot_hops} {incr hop} {
      set inst [$s getInst]
      if {[ot_of_isff $inst]} {
        if {[[$s getMTerm] getName] eq "D"} { set ff $inst }
        break
      }
      if {![ot_of_isbuf $inst]} break
      if {[$inst getPlacementStatus] eq "FIRM"} { set hw [expr {$hw + double([[$inst getMaster] getWidth]) / $ot_dbu}] }
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
  # el1013-smh-r14 2026-10-13: a pin flop the kit already fixed at its own station (FIRM before global placement: the SM
  # tile cluster's strap stage 0 and reset pin flop, placed by its POST_TAPCELL stations) stays there (ODB-0359 otherwise)
  if {[$ff isFixed]} { if {![info exists ot_kept]} { set ot_kept 0 }; incr ot_kept; continue }
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
  lappend cand [list $side [expr {($side eq "L" || $side eq "R") ? $py : $px}] $ff $px $py $io $hw]
}
set cand [lsort -real -index 1 $cand]
# >>> auto spread (extracted and run under tclsh by tools/closure_loop/test_pin_fit.py)
foreach side {L R B T} {
  set ot_k($side) 0; set ot_sgap($side) $ot_gap; set ot_scols($side) $ot_cols
  if {!$ot_au_on} continue
  # densest ot_au_win um of this face: pin flops (cnt) and FIRM hold-cell width (hw) between the pins and their flops
  set pts {}; set fw 1.08
  foreach c $cand {
    if {[lindex $c 0] ne $side} continue
    lappend pts [list [lindex $c 1] [lindex $c 6]]
    set fw [expr {double([[[lindex $c 2] getMaster] getWidth]) / $ot_dbu}]
  }
  set n [llength $pts]; if {$n == 0} continue
  set j 0; set hw 0.0; set mhw 0.0; set mcnt 0
  for {set i 0} {$i < $n} {incr i} {
    set hw [expr {$hw + [lindex $pts $i 1]}]
    while {[lindex $pts $i 0] - [lindex $pts $j 0] > $ot_au_win} { set hw [expr {$hw - [lindex $pts $j 1]}]; incr j }
    if {$hw > $mhw} { set mhw $hw }
    if {$i - $j + 1 > $mcnt} { set mcnt [expr {$i - $j + 1}] }
  }
  set depth [expr {$mhw * $ot_au_row / $ot_au_win}]
  if {$depth < $ot_au_dense} continue
  set vert [expr {$side eq "L" || $side eq "R"}]
  if {!$ot_au_gap_set} { set ot_sgap($side) [expr {max($ot_gap, round($depth * $ot_au_slack * 10.0) / 10.0)}] }
  set dens [expr {$mcnt / $ot_au_win}]
  set need [expr {$vert ? int(ceil($ot_au_cols_v * $dens * $ot_au_row - 1e-9)) : int(ceil($ot_au_cols_h * $dens * ($fw + 0.2) - 1e-9))}]
  if {$need > $ot_scols($side)} { set ot_scols($side) $need }
  # the stages + flop band stay inside ot_au_depth_max of the core behind the face (fewer columns, never a negative site)
  set pitch [expr {$vert ? $fw + 0.2 : $ot_au_row}]
  set room [expr {$ot_au_depth_max * ($vert ? $cx1 - $cx0 : $cy1 - $cy0)}]
  set fit [expr {int(floor(($room - $ot_sgap($side)) / $pitch))}]
  if {$fit < $ot_scols($side)} {
    puts "OT_IOFLOP auto WARNING side $side: gap $ot_sgap($side) um + $ot_scols($side) columns exceed [format %.1f $room] um of core: [expr {max(1, $fit)}] columns (face too dense for this tile depth)"
    set ot_scols($side) [expr {max(1, $fit)}]
  }
  puts [format "OT_IOFLOP auto side %s: %d pin flops / %.0f um, FIRM hold cells %.2f um deep -> gap %.1f um, %d columns (default %s / %d)" \
          $side $mcnt $ot_au_win $depth $ot_sgap($side) $ot_scols($side) $ot_gap $ot_cols]
}
# <<< auto spread
foreach c $cand {
  lassign $c side pos ff px py io
  set col [expr {$ot_k($side) % $ot_scols($side)}]; incr ot_k($side)
  set w [expr {double([[$ff getMaster] getWidth]) / $ot_dbu}]
  set h [expr {double([[$ff getMaster] getHeight]) / $ot_dbu}]
  set sg $ot_sgap($side)
  switch $side {
    L { set x [expr {$cx0 + $sg + $col * ($w + 0.2)}]; set y $py }
    R { set x [expr {$cx1 - $sg - ($col + 1) * ($w + 0.2)}]; set y $py }
    B { set x $px; set y [expr {$cy0 + $sg + $col * $h}] }
    T { set x $px; set y [expr {$cy1 - $sg - ($col + 1) * $h}] }
  }
  if {[[$ff getMaster] isBlock]} {error {standard cell placement refuses BLOCK}}
  $ff setLocation [expr {round($x * $ot_dbu)}] [expr {round($y * $ot_dbu)}]
  $ff setPlacementStatus FIRM
  lappend ot_list [$ff getName]
  if {$io eq "INPUT"} { incr ot_ni } else { incr ot_n }
}
# Keep historical single-capture/output placement byte-for-byte. Only previously
# unanchored captures use the legal-row allocator below, after output ownership
# has been resolved. Thus an output clone retains its output-side anchor.
set ot_extra {}
foreach request $ot_extra_ports {
  lassign $request bt captures
  foreach ff $captures {
    set name [$ff getName]
    if {[dict exists $ot_seen $name]} continue
    dict set ot_seen $name 1
    lappend ot_extra [list [$bt getName] $name $bt $ff]
  }
}
set ot_extra [lsort -dictionary $ot_extra]
if {[llength $ot_extra]} {
  set ot_rows {}
  foreach row [$ot_blk getRows] {
    set box [$row getBBox]
    lappend ot_rows [list [$box yMin] [$box xMin] [$box xMax] [$box yMax] \
      [$row getSpacing] [$row getOrient]]
  }
  set ot_rows [lsort -integer -index 0 $ot_rows]
  # Reserve all firm/fixed footprints, including existing pin anchors and stages.
  set ot_occupied [dict create]
  foreach inst [$ot_blk getInsts] {
    if {[$inst getPlacementStatus] ni {FIRM LOCKED COVER}} continue
    set box [$inst getBBox]
    set ri 0
    foreach row $ot_rows {
      lassign $row ry rx ex ey pitch orient
      if {[$box yMin] < $ey && [$box yMax] > $ry} {
        dict lappend ot_occupied $ri [list [$box xMin] [$box xMax]]
      }
      incr ri
    }
  }
  foreach blockage [$ot_blk getBlockages] {
    set box [$blockage getBBox]
    set ri 0
    foreach row $ot_rows {
      lassign $row ry rx ex ey pitch orient
      if {[$box yMin] < $ey && [$box yMax] > $ry} {
        dict lappend ot_occupied $ri [list [$box xMin] [$box xMax]]
      }
      incr ri
    }
  }
  foreach request $ot_extra {
    lassign $request port name bt ff
    set box [$bt getBBox]
    set px [expr {([$box xMin] + [$box xMax]) / 2.0}]
    set py [expr {([$box yMin] + [$box yMax]) / 2.0}]
    set width [[$ff getMaster] getWidth]; set height [[$ff getMaster] getHeight]
    set best {}; set score Inf; set ri 0
    foreach row $ot_rows {
      lassign $row ry rx ex ey pitch orient
      if {$height != $ey - $ry || $pitch <= 0} { incr ri; continue }
      set blocks {}
      if {[dict exists $ot_occupied $ri]} { set blocks [lsort -integer -index 0 [dict get $ot_occupied $ri]] }
      lappend blocks [list $ex $ex]
      set start $rx
      foreach block $blocks {
        lassign $block lo hi
        set low [expr {$rx + int(ceil(double($start - $rx) / $pitch)) * $pitch}]
        set high [expr {$rx + int(floor(double(min($lo, $ex) - $width - $rx) / $pitch)) * $pitch}]
        if {$high >= $low} {
          set x [expr {max($low, min($high, $rx + round(($px - $width / 2.0 - $rx) / $pitch) * $pitch))}]
          set cost [expr {abs($x + $width / 2.0 - $px) + abs($ry + $height / 2.0 - $py)}]
          if {$cost < $score} { set score $cost; set best [list $ri $x $ry $orient] }
        }
        set start [expr {max($start, $hi)}]
      }
      incr ri
    }
    if {$best eq ""} { error "OT_IOFLOP: no legal capture site for $name ($port)" }
    lassign $best ri x y orient
    $ff setOrient $orient
    if {[[$ff getMaster] isBlock]} {error {standard cell placement refuses BLOCK}}
    $ff setLocation $x $y
    $ff setPlacementStatus FIRM
    dict lappend ot_occupied $ri [list $x [expr {$x + $width}]]
    lappend ot_list $name
    incr ot_ni
    puts "OT_IOFLOP extra capture $port -> $name at ($x, $y) DBU"
  }
}
# OT_MPFLOP_PINS (el1011-q-kvd 2026-10-12, optional; comma-separated pin names, e.g. "pop"): also anchor the flop that
# drives each such INPUT pin of a hard macro / hardened child (directly or through <= 3 single-fanout INV / BUF), FIRM
# just outside the macro halo (OT_MPFLOP_GAP um, default 2.7) on the macro edge nearest the pin.  qkd_d2d_ref-q8-aeca40e24:
# the sbuf pop pin is a ~660 ps internal cone, so the parent may spend only ~110 ps (clk->Q + wire) on it -- the RTL
# drives it from a dedicated flop (ot_qkvd_d2d PQ), this places that flop at the pin.  Released at PRE_DETAIL_PLACE with
# the port flops (same list file).  Placement only, 0 cycles.
set ot_nm 0
if {[info exists ::env(OT_MPFLOP_PINS)] && $::env(OT_MPFLOP_PINS) ne ""} {
  set mpins [split $::env(OT_MPFLOP_PINS) ","]
  set mgap [expr {[info exists ::env(OT_MPFLOP_GAP)] ? $::env(OT_MPFLOP_GAP) : 2.7}]
  set mskip 0
  foreach inst [$ot_blk getInsts] {
    if {![[$inst getMaster] isBlock]} continue
    set mb [$inst getBBox]
    set mx0 [expr {double([$mb xMin]) / $ot_dbu}]; set mx1 [expr {double([$mb xMax]) / $ot_dbu}]
    set my0 [expr {double([$mb yMin]) / $ot_dbu}]; set my1 [expr {double([$mb yMax]) / $ot_dbu}]
    foreach it [$inst getITerms] {
      if {![$it isInputSignal] || [lsearch -exact $mpins [[$it getMTerm] getName]] < 0} continue
      set net [$it getNet]; if {$net eq "NULL"} { incr mskip; continue }
      set d [ot_of_drv $net]; if {$d eq ""} { incr mskip; continue }
      set ff ""; set fi [$d getInst]
      for {set hop 0} {$hop < 4} {incr hop} {
        if {[ot_of_isff $fi]} { set ff $fi; break }
        if {![ot_of_isbuf $fi]} break
        set nxt ""
        foreach i2 [$fi getITerms] {
          if {![$i2 isInputSignal]} continue
          set n2 [$i2 getNet]; if {$n2 eq "NULL"} continue
          set d2 [ot_of_drv $n2]
          if {$d2 ne "" && [llength [$n2 getITerms]] == 2} { set nxt [$d2 getInst] }
        }
        if {$nxt eq ""} break
        set fi $nxt
      }
      if {$ff eq ""} { incr mskip; puts "OT_MPFLOP skip [$inst getName]/[[$it getMTerm] getName]: driver is not a flop"; continue }
      set fn [$ff getName]
      if {[dict exists $ot_seen $fn]} continue
      dict set ot_seen $fn 1
      if {[catch {set pb [$it getBBox]}] || $pb eq "" || $pb eq "NULL"} {
        set px [expr {($mx0 + $mx1) / 2.0}]; set py [expr {($my0 + $my1) / 2.0}]
      } else {
        set px [expr {double([$pb xMin] + [$pb xMax]) / 2.0 / $ot_dbu}]; set py [expr {double([$pb yMin] + [$pb yMax]) / 2.0 / $ot_dbu}]
      }
      set w [expr {double([[$ff getMaster] getWidth]) / $ot_dbu}]
      set h [expr {double([[$ff getMaster] getHeight]) / $ot_dbu}]
      set dl [expr {$px - $mx0}]; set dr [expr {$mx1 - $px}]; set dbo [expr {$py - $my0}]; set dt [expr {$my1 - $py}]
      set dm [expr {min($dl, $dr, $dbo, $dt)}]
      if {$dl == $dm} { set x [expr {$mx0 - $mgap - $w}]; set y $py
      } elseif {$dr == $dm} { set x [expr {$mx1 + $mgap}]; set y $py
      } elseif {$dbo == $dm} { set x $px; set y [expr {$my0 - $mgap - $h}]
      } else { set x $px; set y [expr {$my1 + $mgap}] }
      set x [expr {max($cx0, min($x, $cx1 - $w))}]; set y [expr {max($cy0, min($y, $cy1 - $h))}]
      if {[[$ff getMaster] isBlock]} {error {standard cell placement refuses BLOCK}}
      $ff setLocation [expr {round($x * $ot_dbu)}] [expr {round($y * $ot_dbu)}]
      $ff setPlacementStatus FIRM
      lappend ot_list $fn
      incr ot_nm
      puts [format "OT_MPFLOP %s -> %s/%s at (%.2f, %.2f)" $fn [$inst getName] [[$it getMTerm] getName] $x $y]
    }
  }
  puts "OT_MPFLOP fixed $ot_nm macro-input-pin flops beside their pins ($mskip pins not flop-driven)"
  if {$ot_nm == 0} { error "OT_MPFLOP: OT_MPFLOP_PINS=$::env(OT_MPFLOP_PINS) matched no flop-driven macro pin (netlist changed?)" }
}
# OT_MPCAP_PINS (S-ELEM-B 2026-10-15, optional; comma-separated hard-macro OUTPUT bus base names, e.g. "rd_out"): anchor the
# flop that CAPTURES each such macro output bit (the output net's single data sink, followed through <= 2 single-output
# cells such as the capture-enable mux), FIRM just outside the macro halo on the macro edge nearest the pin.  calendar7
# c2: the ROM clk->q is 586-609 ps of 833, so the capture flop may spend only ~80 ps on wire + mux + setup; unanchored, the
# placer pulled the 565 capture flops toward their output-port consumers (63 ps wire + 51 ps buffer from the ROM pin).
# Released at PRE_DETAIL_PLACE with the port flops (same list file).  Placement only, 0 cycles.
if {[info exists ::env(OT_MPCAP_PINS)] && $::env(OT_MPCAP_PINS) ne ""} {
  set cpins [split $::env(OT_MPCAP_PINS) ","]
  set cgap [expr {[info exists ::env(OT_MPCAP_GAP)] ? $::env(OT_MPCAP_GAP) : 2.7}]
  set cskip 0; set ot_nc 0
  foreach inst [$ot_blk getInsts] {
    if {![[$inst getMaster] isBlock]} continue
    set mb [$inst getBBox]
    set mx0 [expr {double([$mb xMin]) / $ot_dbu}]; set mx1 [expr {double([$mb xMax]) / $ot_dbu}]
    set my0 [expr {double([$mb yMin]) / $ot_dbu}]; set my1 [expr {double([$mb yMax]) / $ot_dbu}]
    foreach it [$inst getITerms] {
      if {![$it isOutputSignal]} continue
      set base [regsub {\[[0-9]+\]$} [[$it getMTerm] getName] ""]
      if {[lsearch -exact $cpins $base] < 0} continue
      set net [$it getNet]; if {$net eq "NULL"} continue
      set ff ""
      for {set hop 0} {$hop < 3} {incr hop} {
        set s [ot_of_sink $net]; if {$s eq ""} break
        set si [$s getInst]
        if {[ot_of_isff $si]} { if {[[$s getMTerm] getName] eq "D"} { set ff $si }; break }
        set onet ""; set nout 0
        foreach o [$si getITerms] { if {[$o isOutputSignal]} { incr nout; set onet [$o getNet] } }
        if {$nout != 1 || $onet eq "" || $onet eq "NULL"} break
        set net $onet
      }
      if {$ff eq ""} { incr cskip; continue }
      set fn [$ff getName]
      if {[dict exists $ot_seen $fn]} continue
      dict set ot_seen $fn 1
      if {[catch {set pb [$it getBBox]}] || $pb eq "" || $pb eq "NULL"} {
        set px [expr {($mx0 + $mx1) / 2.0}]; set py [expr {($my0 + $my1) / 2.0}]
      } else {
        set px [expr {double([$pb xMin] + [$pb xMax]) / 2.0 / $ot_dbu}]; set py [expr {double([$pb yMin] + [$pb yMax]) / 2.0 / $ot_dbu}]
      }
      set w [expr {double([[$ff getMaster] getWidth]) / $ot_dbu}]
      set h [expr {double([[$ff getMaster] getHeight]) / $ot_dbu}]
      set dl [expr {$px - $mx0}]; set dr [expr {$mx1 - $px}]; set dbo [expr {$py - $my0}]; set dt [expr {$my1 - $py}]
      set dm [expr {min($dl, $dr, $dbo, $dt)}]
      if {$dl == $dm} { set x [expr {$mx0 - $cgap - $w}]; set y $py
      } elseif {$dr == $dm} { set x [expr {$mx1 + $cgap}]; set y $py
      } elseif {$dbo == $dm} { set x $px; set y [expr {$my0 - $cgap - $h}]
      } else { set x $px; set y [expr {$my1 + $cgap}] }
      set x [expr {max($cx0, min($x, $cx1 - $w))}]; set y [expr {max($cy0, min($y, $cy1 - $h))}]
      $ff setLocation [expr {round($x * $ot_dbu)}] [expr {round($y * $ot_dbu)}]
      $ff setPlacementStatus FIRM
      lappend ot_list $fn
      incr ot_nc
    }
  }
  puts "OT_MPCAP fixed $ot_nc macro-output capture flops beside their pins ($cskip connected pins without a single capture flop)"
  if {$ot_nc == 0} { error "OT_MPCAP: OT_MPCAP_PINS=$::env(OT_MPCAP_PINS) matched no captured macro output (netlist changed?)" }
}
# Resolve actual FIRM overlaps without changing the native boundary circuit.
# The hold hooks record exactly the cells they own; unrelated FIRM cells and
# hard macros are obstacles, not candidates for movement.
set ot_pack_names $ot_list
set ot_pack_record $::env(RESULTS_DIR)/ot_inhold_firm.txt
if {[file exists $ot_pack_record]} {
  set ot_pack_file [open $ot_pack_record r]
  foreach ot_pack_name [split [read $ot_pack_file] \n] {
    if {$ot_pack_name ne ""} {lappend ot_pack_names $ot_pack_name}
  }
  close $ot_pack_file
}
source /src/physical/common_flow/anchor_row_packing.tcl
ot_anchor_pack::repair $ot_blk $ot_pack_names
set fh [open $::env(RESULTS_DIR)/ot_out_flop_at_pins.txt w]
foreach n $ot_list { puts $fh $n }
close $fh
puts "OT_IOFLOP fixed $ot_n output-port and $ot_ni input-port flops at their pins ($ot_skip ports not single-flop)"
if {[info exists ot_kept]} { puts "OT_IOFLOP kept $ot_kept pin flops the kit had already fixed at their own stations" }
if {$ot_n + $ot_ni == 0 && !$ot_allow_none && $ot_verified_hard_faces == 0} { error "OT_IOFLOP: no pin flop found (netlist changed?)" }
