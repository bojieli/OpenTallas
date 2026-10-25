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
set ot_mpf_blk [ord::get_db_block]
set ot_mpf_dbu [[ord::get_db_tech] getDbUnitsPerMicron]
proc ot_mpf_env {k d} { expr {[info exists ::env($k)] && $::env($k) ne "" ? $::env($k) : $d} }
set ot_mpf_hops [ot_mpf_env OT_MPF_HOPS 4]
set ot_mpf_gap [ot_mpf_env OT_MPF_GAP_UM 0.54]
set ot_mpf_halo [ot_mpf_env OT_MPF_HALO_UM [ot_mpf_env MACRO_ROWS_HALO_X 5.4]]
set ot_mpf_core [$ot_mpf_blk getCoreArea]
# OT_MPF_TREE=1 (QC-CQB2 2026-10-25, opt-in): a write-landing flop may also fan out through a buffer / inverter TREE
# (any fanout per stage) as long as every leaf is an input pin of the same ONE hard macro (vmr_cqb: each w_mask landing
# flop g_mw[i].u_m/q[k] drives 32 w_mask_in pins through 32 INVx3; without this they stayed 165-190 um from their pins).
# Anchored at the centroid of its leaf pins.  Unset: unchanged single-fanout rule.
# OT_MPF_SHARED=1 (with OT_MPF_TREE): the tree may also reach other logic, if it reaches at least as many pins of the ONE
# macro as other loads (vmr_cqb: the write-address / write-enable landing flops g_mw[i].u_r / u_e feed the SRAM
# w_addr_in / w_ce_in pin AND one read/write address-compare gate each; they stayed 92-224 um from their pins).
set ot_mpf_tree [ot_mpf_env OT_MPF_TREE 0]
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
# (a) macro output pin -> the single flop it feeds (D pin)
proc ot_mpf_capture {net hops} {
  for {set h 0} {$h <= $hops} {incr h} {
    if {[ot_mpf_nports $net]} { return "" }
    set s [ot_mpf_sinks $net]; if {[llength $s] != 1} { return "" }
    set it [lindex $s 0]; set inst [$it getInst]
    if {[ot_mpf_isff $inst]} { return [expr {[[$it getMTerm] getName] eq "D" ? $inst : ""}] }
    if {![ot_mpf_isbuf $inst]} { return "" }
    set net [ot_mpf_out_net $inst]; if {$net eq ""} { return "" }
  }
  return ""
}
# (b) flop -> its sink pins through single-fanout buffers; returns the sink ITerms if they are ALL pins of one macro
proc ot_mpf_launch_tree {ff hops} {
  # every leaf of the buffer/inverter fanout tree of ff must be an input pin of one macro
  set todo [list [list [ot_mpf_out_net $ff] 0]]; set m ""; set leaves {}; set other 0
  set shared [ot_mpf_env OT_MPF_SHARED 0]
  while {[llength $todo]} {
    lassign [lindex $todo end] net d; set todo [lrange $todo 0 end-1]
    if {$net eq "" || [ot_mpf_nports $net]} { return "" }
    set s [ot_mpf_sinks $net]; if {![llength $s]} { return "" }
    foreach it $s {
      set i [$it getInst]
      if {[[$i getMaster] isBlock]} {
        if {$m eq ""} { set m $i } elseif {$m ne $i} { return "" }
        lappend leaves $it
      } elseif {[ot_mpf_isbuf $i] && $d < $hops} {
        lappend todo [list [ot_mpf_out_net $i] [expr {$d + 1}]]
      } elseif {$shared} { incr other } else { return "" }
    }
  }
  if {$other > [llength $leaves]} { return "" }
  return $leaves
}
proc ot_mpf_launch_sinks {ff hops} {
  if {[ot_mpf_env OT_MPF_TREE 0]} { return [ot_mpf_launch_tree $ff $hops] }
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
      set ff [ot_mpf_capture $net $ot_mpf_hops]
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
        if {(!$ot_mpf_tree && [llength [ot_mpf_sinks $n2]] != 1) || [ot_mpf_nports $n2]} break
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
