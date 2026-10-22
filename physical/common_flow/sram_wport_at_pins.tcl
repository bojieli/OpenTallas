# PRE_GLOBAL_PLACE hook (HBMc/TILES2 2026-10-22, hidx_link r7a/r7b): every SRAM WRITE-PORT register at its macro pin.
# Why: hidx_link r6a/r6b (84e741722) stalled 2.9 h in GRT setup repair at -20.9 ps on all 196 ot_sram_* wd_in endpoints:
# the per-macro write registers (we_n / wa_n / wd_n: RTL "beside each macro") were placed by timing-driven GPL into the
# slice logic, so register -> wd_in carried a long wire inside a half (r6, negedge) or full (r7a, posedge) cycle.
# For each ot_sram_* macro, every w_ce_in / w_addr_in / wd_in pin whose net has exactly one driver -- a DFF, or an INV /
# BUF whose input net is driven by a DFF with no other load -- and no other sink gets that DFF (and the INV / BUF) placed
# FIRM just outside the macro halo on the pin's own side (or the channel side when that side faces the core edge), in 4
# staggered columns.  sram_wport_release.tcl (PRE_DETAIL_PLACE) returns them to PLACED for DPL.  Placement only,
# netlist unchanged, 0 cycles.  The macro CTS cluster (macro_cts_cluster.tcl) keeps the macro clock pin on a short leaf.
set ot_blk [ord::get_db_block]
set ot_dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set ot_core [$ot_blk getCoreArea]
set ot_cx0 [expr {double([$ot_core xMin]) / $ot_dbu}]
set ot_cx1 [expr {double([$ot_core xMax]) / $ot_dbu}]
set ot_halo [expr {[info exists ::env(OT_SWP_HALO)] ? $::env(OT_SWP_HALO) : 5.4}]
set ot_gap 0.6
set ot_swp_list {}
set ot_swp_n 0; set ot_swp_skip 0
proc ot_swp_isff {inst} { return [string match "*DFF*" [[$inst getMaster] getName]] }
foreach ot_m [$ot_blk getInsts] {
  if {![[$ot_m getMaster] isBlock]} continue
  if {![string match "ot_sram_*" [[$ot_m getMaster] getName]]} continue
  set b [$ot_m getBBox]
  set mx0 [expr {double([$b xMin]) / $ot_dbu}]; set mx1 [expr {double([$b xMax]) / $ot_dbu}]
  set left_ok  [expr {($mx0 - $ot_halo - $ot_cx0) > 8.0}]
  set right_ok [expr {($ot_cx1 - $mx1 - $ot_halo) > 8.0}]
  set ot_k(L) 0; set ot_k(R) 0
  foreach it [$ot_m getITerms] {
    set pn [[$it getMTerm] getName]
    if {![string match "w_ce_in*" $pn] && ![string match "w_addr_in*" $pn] && ![string match "wd_in*" $pn]} continue
    set net [$it getNet]
    if {$net eq "NULL" || $net eq ""} continue
    set drv ""; set nother 0
    foreach s [$net getITerms] {
      if {$s eq $it} continue
      if {[$s isOutputSignal]} { set drv [$s getInst] } else { incr nother }
    }
    if {$drv eq "" || $nother != 0} { incr ot_swp_skip; continue }
    set chain {}
    if {[ot_swp_isff $drv]} {
      set chain [list $drv]
    } elseif {[string match "INV*" [[$drv getMaster] getName]] || [string match "BUF*" [[$drv getMaster] getName]]} {
      foreach ii [$drv getITerms] {
        if {![$ii isInputSignal]} continue
        set n2 [$ii getNet]
        if {$n2 eq "NULL" || $n2 eq ""} continue
        set f2 ""; set o2 0
        foreach s2 [$n2 getITerms] {
          if {$s2 eq $ii} continue
          if {[$s2 isOutputSignal] && [ot_swp_isff [$s2 getInst]]} { set f2 [$s2 getInst] } else { incr o2 }
        }
        if {$f2 ne "" && $o2 == 0} { set chain [list $drv $f2] }
      }
    }
    if {![llength $chain]} { incr ot_swp_skip; continue }
    set ff [lindex $chain end]
    if {[lsearch -exact $ot_swp_list [$ff getName]] >= 0} continue
    set xy [$it getAvgXY]
    set px [expr {double([lindex $xy 1]) / $ot_dbu}]
    set py [expr {double([lindex $xy 2]) / $ot_dbu}]
    set side [expr {$px < ($mx0 + $mx1) / 2.0 ? "L" : "R"}]
    if {$side eq "L" && !$left_ok} { set side R }
    if {$side eq "R" && !$right_ok} { set side L }
    set col [expr {$ot_k($side) % 4}]; incr ot_k($side)
    set ox [expr {$ot_halo + $ot_gap + $col * 2.4}]
    # flop nearest the macro, then the INV / BUF (if any) between it and the pin
    foreach c [lreverse $chain] {
      set w [expr {double([[$c getMaster] getWidth]) / $ot_dbu}]
      if {$side eq "L"} { set x [expr {$mx0 - $ox - $w}] } else { set x [expr {$mx1 + $ox}] }
      set ox [expr {$ox + $w + 0.2}]
      $c setLocation [expr {round($x * $ot_dbu)}] [expr {round($py * $ot_dbu)}]
      $c setPlacementStatus FIRM
      lappend ot_swp_list [$c getName]
    }
    incr ot_swp_n
  }
}
set fh [open $::env(RESULTS_DIR)/ot_sram_wport_firm.txt w]
foreach n $ot_swp_list { puts $fh $n }
close $fh
puts "OT_SWP anchored $ot_swp_n SRAM write-port pins ([llength $ot_swp_list] cells FIRM), skipped $ot_swp_skip"
