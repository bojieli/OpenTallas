# PRE_GLOBAL_PLACE hook (STW-S81c-COLLA2-TX 2026-10-22): MACRO-PIN FLOPS at their hard-macro pins.
# A macro-pin flop is (a) a register whose D is driven by ONE hard-macro output pin (e.g. an SRAM rd_out capture flop),
# through at most OT_MPF_HOPS single-fanout INV / BUF / HB cells, or (b) a register whose Q (through at most OT_MPF_HOPS
# single-fanout INV / BUF / HB cells) drives ONLY input pins of ONE hard macro (write-port landing flops wd_l / wa_l /
# we_l, mask copies).  Why (s81dv_idxtxn32t-h-6ec9980cf, TOPK TX t TT -55.6): the RDL capture q_l of banks 5-7 sat
# ~150 um from its rd_out pin (pulled toward the bank read mux in the mid band): macro clk->q 550 ps + 283 ps wire.
# The flop is anchored FIRM just outside the macro halo at the pin (centroid of its pins for case b), on the pin's
# edge side; anchor_row_packing.tcl legalises overlaps; macro_pin_flops_release.tcl (PRE_DETAIL_PLACE) returns them to
# PLACED.  Placement only, 0 cycles, no netlist / SDC change.
#   OT_MPF_HOPS (default 4)   OT_MPF_GAP_UM (default 0.54: clearance beyond the halo)
#   OT_MPF_HALO_UM (default MACRO_ROWS_HALO_X, else 5.4)
#   OT_MPF_ENMUX (default 0; PATH-S81/E4 10-25): also accept a read capture whose D is reached through at most
#     OT_MPF_ENMUX_HOPS (default 2) single-fanout combinational std cells, provided one of them takes the capture flop's
#     OWN Q / QN as an input (directly or through <= 2 std cells) = the enable-feedback mux Yosys maps a DFFE to on ASAP7 (DFFHQN + NAND2 / OAI21 hold
#     loop, or AO21 + AND2(INV(QN), !en): S81 eng CPRE bank_words, 0/544 ROM captures anchored without it).  Any other gate cone is still refused.
set ot_mpf_blk [ord::get_db_block]
set ot_mpf_dbu [[ord::get_db_tech] getDbUnitsPerMicron]
proc ot_mpf_env {k d} { expr {[info exists ::env($k)] && $::env($k) ne "" ? $::env($k) : $d} }
set ot_mpf_hops [ot_mpf_env OT_MPF_HOPS 4]
set ot_mpf_gap [ot_mpf_env OT_MPF_GAP_UM 0.54]
set ot_mpf_halo [ot_mpf_env OT_MPF_HALO_UM [ot_mpf_env MACRO_ROWS_HALO_X 5.4]]
set ot_mpf_enmux [ot_mpf_env OT_MPF_ENMUX 0]
set ot_mpf_enmux_hops [ot_mpf_env OT_MPF_ENMUX_HOPS 2]
set ot_mpf_core [$ot_mpf_blk getCoreArea]
proc ot_mpf_isff {inst} { set m [[$inst getMaster] getName]; expr {[string match "DFF*" $m] || [string match "ASYNC_DFF*" $m]} }
proc ot_mpf_isbuf {inst} { set m [[$inst getMaster] getName]; expr {[string match "INV*" $m] || [string match "BUF*" $m] || [string match "HB*" $m]} }
proc ot_mpf_sinks {net} { set s {}; foreach it [$net getITerms] { if {[$it isInputSignal]} { lappend s $it } }; return $s }
proc ot_mpf_nports {net} { set n 0; foreach bt [$net getBTerms] { incr n }; return $n }
proc ot_mpf_out_net {inst} { foreach it [$inst getITerms] { if {[$it isOutputSignal] && [$it getNet] ne "NULL"} { return [$it getNet] } }; return "" }
proc ot_mpf_in_net {inst} { foreach it [$inst getITerms] { if {[$it isInputSignal] && [$it getNet] ne "NULL"} { return [$it getNet] } }; return "" }
proc ot_mpf_drv {net} { foreach it [$net getITerms] { if {[$it isOutputSignal]} { return $it } }; return "" }
proc ot_mpf_xy {it dbu} {
  set bb [$it getBBox]
  return [list [expr {double([$bb xMin] + [$bb xMax]) / 2.0 / $dbu}] [expr {double([$bb yMin] + [$bb yMax]) / 2.0 / $dbu}]]
}
# (a) macro output pin -> the single flop it feeds (D pin); with OT_MPF_ENMUX also through the DFFE enable-feedback
# gates (single-fanout std cells, <= enmux_hops of them, one of which reads the capture flop's own Q / QN)
proc ot_mpf_isgate {inst} {
  set m [$inst getMaster]
  if {[$m isBlock] || [$m isSequential]} { return 0 }
  set no 0; foreach it [$inst getITerms] { if {[$it isOutputSignal]} { incr no } }
  expr {$no == 1}
}
proc ot_mpf_reads {net qs depth} {
  if {[$net getName] in $qs} { return 1 }
  if {$depth <= 0} { return 0 }
  set d [ot_mpf_drv $net]; if {$d eq ""} { return 0 }
  set i [$d getInst]; if {![ot_mpf_isgate $i]} { return 0 }
  foreach t [$i getITerms] { if {[$t isInputSignal] && [$t getNet] ne "NULL" && [ot_mpf_reads [$t getNet] $qs [expr {$depth - 1}]]} { return 1 } }
  return 0
}
proc ot_mpf_capture {net hops {enmux 0} {gate_hops 2}} {
  set gates {}
  for {set h 0} {$h <= $hops + $gate_hops} {incr h} {
    if {[ot_mpf_nports $net]} { return "" }
    set s [ot_mpf_sinks $net]; if {[llength $s] != 1} { return "" }
    set it [lindex $s 0]; set inst [$it getInst]
    if {[ot_mpf_isff $inst]} {
      if {[[$it getMTerm] getName] ne "D"} { return "" }
      if {![llength $gates]} { return $inst }
      # enable-feedback signature: some traversed gate reads this flop's own output, directly or through <= 2 std
      # cells (AO21 hold form: D = q_rom & en | AND2(INV(QN), !en))
      set qs {}
      foreach o [$inst getITerms] { if {[$o isOutputSignal] && [$o getNet] ne "NULL"} { lappend qs [[$o getNet] getName] } }
      foreach g $gates { foreach gi [$g getITerms] {
        if {[$gi isInputSignal] && [$gi getNet] ne "NULL" && [ot_mpf_reads [$gi getNet] $qs 2]} { return $inst }
      } }
      return ""
    }
    if {[ot_mpf_isbuf $inst]} {
    } elseif {$enmux && [llength $gates] < $gate_hops && [ot_mpf_isgate $inst]} {
      lappend gates $inst
    } else { return "" }
    set net [ot_mpf_out_net $inst]; if {$net eq ""} { return "" }
  }
  return ""
}
# (b) flop -> its sink pins through single-fanout buffers; returns the sink ITerms if they are ALL pins of one macro
proc ot_mpf_launch_sinks {ff hops} {
  set net [ot_mpf_out_net $ff]; if {$net eq ""} { return "" }
  for {set h 0} {$h <= $hops} {incr h} {
    if {[ot_mpf_nports $net]} { return "" }
    set s [ot_mpf_sinks $net]; if {![llength $s]} { return "" }
    if {[llength $s] == 1 && [ot_mpf_isbuf [[lindex $s 0] getInst]]} {
      set net [ot_mpf_out_net [[lindex $s 0] getInst]]; if {$net eq ""} { return "" }; continue
    }
    set m ""
    foreach it $s {
      set i [$it getInst]
      if {![[$i getMaster] isBlock]} { return "" }
      if {$m eq ""} { set m $i } elseif {$m ne $i} { return "" }
    }
    return $s
  }
  return ""
}
set cx0 [expr {double([$ot_mpf_core xMin]) / $ot_mpf_dbu}]; set cx1 [expr {double([$ot_mpf_core xMax]) / $ot_mpf_dbu}]
set cy0 [expr {double([$ot_mpf_core yMin]) / $ot_mpf_dbu}]; set cy1 [expr {double([$ot_mpf_core yMax]) / $ot_mpf_dbu}]
set ot_mpf_list {}; set ot_mpf_seen [dict create]; set ot_mpf_na 0; set ot_mpf_nb 0
proc ot_mpf_anchor {ff mac px py} {
  # the hook may be sourced inside an ORFS proc: take the caller's variables, never globals
  upvar 1 ot_mpf_list lst ot_mpf_seen seen ot_mpf_dbu ot_mpf_dbu ot_mpf_halo ot_mpf_halo ot_mpf_gap ot_mpf_gap cx0 cx0 cx1 cx1 cy0 cy0 cy1 cy1
  set mb [$mac getBBox]
  set mx0 [expr {double([$mb xMin]) / $ot_mpf_dbu}]; set mx1 [expr {double([$mb xMax]) / $ot_mpf_dbu}]
  set my0 [expr {double([$mb yMin]) / $ot_mpf_dbu}]; set my1 [expr {double([$mb yMax]) / $ot_mpf_dbu}]
  set w [expr {double([[$ff getMaster] getWidth]) / $ot_mpf_dbu}]
  set h [expr {double([[$ff getMaster] getHeight]) / $ot_mpf_dbu}]
  # nearest macro edge to the pin decides the side
  set dl [expr {abs($px - $mx0)}]; set dr [expr {abs($mx1 - $px)}]; set db [expr {abs($py - $my0)}]; set dt [expr {abs($my1 - $py)}]
  set dm [expr {min($dl, $dr, $db, $dt)}]
  set off [expr {$ot_mpf_halo + $ot_mpf_gap}]
  if {$dm == $dl} { set x [expr {$mx0 - $off - $w}]; set y [expr {$py - $h / 2.0}]
  } elseif {$dm == $dr} { set x [expr {$mx1 + $off}]; set y [expr {$py - $h / 2.0}]
  } elseif {$dm == $db} { set x [expr {$px - $w / 2.0}]; set y [expr {$my0 - $off - $h}]
  } else { set x [expr {$px - $w / 2.0}]; set y [expr {$my1 + $off}] }
  set x [expr {min(max($x, $cx0), $cx1 - $w)}]
  set y [expr {min(max($y, $cy0), $cy1 - $h)}]
  set y [expr {$cy0 + round(($y - $cy0) / $h) * $h}]
  $ff setLocation [expr {round($x * $ot_mpf_dbu)}] [expr {round($y * $ot_mpf_dbu)}]
  $ff setPlacementStatus FIRM
  dict set seen [$ff getName] 1
  lappend lst [$ff getName]
}
foreach mac [$ot_mpf_blk getInsts] {
  if {![[$mac getMaster] isBlock]} continue
  foreach it [$mac getITerms] {
    set net [$it getNet]; if {$net eq "NULL" || $net eq ""} continue
    if {[$net getSigType] in {POWER GROUND CLOCK}} continue
    if {[[$it getMTerm] getSigType] eq "CLOCK"} continue
    if {[$it isOutputSignal]} {
      set ff [ot_mpf_capture $net $ot_mpf_hops $ot_mpf_enmux $ot_mpf_enmux_hops]
      if {$ff eq "" || [$ff isFixed] || [$ff getPlacementStatus] eq "FIRM" || [dict exists $ot_mpf_seen [$ff getName]]} continue
      lassign [ot_mpf_xy $it $ot_mpf_dbu] px py
      ot_mpf_anchor $ff $mac $px $py; incr ot_mpf_na
    } elseif {[$it isInputSignal]} {
      # walk back from the pin through single-fanout buffers to a flop
      set d [ot_mpf_drv $net]; set ff ""
      for {set h 0} {$h <= $ot_mpf_hops && $d ne ""} {incr h} {
        set i [$d getInst]
        if {[ot_mpf_isff $i]} { set ff $i; break }
        if {![ot_mpf_isbuf $i]} break
        set n2 [ot_mpf_in_net $i]; if {$n2 eq ""} break
        if {[llength [ot_mpf_sinks $n2]] != 1 || [ot_mpf_nports $n2]} break
        set d [ot_mpf_drv $n2]
      }
      if {$ff eq "" || [$ff isFixed] || [$ff getPlacementStatus] eq "FIRM" || [dict exists $ot_mpf_seen [$ff getName]]} continue
      set s [ot_mpf_launch_sinks $ff $ot_mpf_hops]; if {$s eq ""} continue
      set sx 0.0; set sy 0.0
      foreach p $s { lassign [ot_mpf_xy $p $ot_mpf_dbu] a b; set sx [expr {$sx + $a}]; set sy [expr {$sy + $b}] }
      ot_mpf_anchor $ff $mac [expr {$sx / [llength $s]}] [expr {$sy / [llength $s]}]; incr ot_mpf_nb
    }
  }
}
if {[llength $ot_mpf_list]} {
  set ot_anchor_script /src/physical/common_flow/anchor_row_packing.tcl
  if {![file exists $ot_anchor_script] && [info script] ne ""} {
    set ot_anchor_script [file join [file dirname [info script]] anchor_row_packing.tcl]
  }
  source $ot_anchor_script
  ot_anchor_pack::repair $ot_mpf_blk $ot_mpf_list
}
set fh [open $::env(RESULTS_DIR)/ot_macro_pin_flops.txt w]
foreach n $ot_mpf_list { puts $fh $n }
close $fh
puts "OT_MPF anchored [llength $ot_mpf_list] macro-pin flops ($ot_mpf_na read captures, $ot_mpf_nb write landings) outside the [format %.2f $ot_mpf_halo] um halo"
