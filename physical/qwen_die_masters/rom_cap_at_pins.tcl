# PRE_GLOBAL_PLACE hook (qwen-tile 2026-10-08): put every ROM output capture register AT its macro pin.
# Why: qfd_tile_rp1 (ROM_PIPE=1) routed TT -369 at detail place / -284 post-CTS on ROM rd_out -> g_rom_pipe...cap:
# ROM clk->q 593 ps TT, then ~460 ps of wire (3 BUFx16f hops) because timing-driven GPL pulled the 1,280 caps into
# the logic band, 400-600 um from their banks.  The RTL intends "the bank's output register at its pins"; this hook
# makes the layout match: for each ot_rom_* macro, every rd_out pin's sole DFF sink (by connectivity, not by name)
# is placed FIRM just outside the macro halo on the pin's own side, or on the opposite (channel) side when the pin
# edge faces the core boundary.  GPL then places the downstream BF16 expansion / group OR around the fixed caps.
# rom_cap_release.tcl (PRE_DETAIL_PLACE) returns them to PLACED so DPL legalises them (tap / overlap clean-up).
# Placement only: netlist unchanged, 0 cycles.
set ot_blk [ord::get_db_block]
set ot_dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set ot_core [$ot_blk getCoreArea]
set ot_cx0 [expr {double([$ot_core xMin]) / $ot_dbu}]
set ot_cx1 [expr {double([$ot_core xMax]) / $ot_dbu}]
set ot_halo [expr {[info exists ::env(OT_PCAP_HALO)] ? $::env(OT_PCAP_HALO) : 2.16}]
set ot_gap 0.6
set ot_list {}
set ot_n 0
set ot_far 0
foreach ot_m [$ot_blk getInsts] {
  if {![[$ot_m getMaster] isBlock]} continue
  if {![string match "ot_rom_*" [[$ot_m getMaster] getName]]} continue
  set b [$ot_m getBBox]
  set mx0 [expr {double([$b xMin]) / $ot_dbu}]; set mx1 [expr {double([$b xMax]) / $ot_dbu}]
  set left_ok  [expr {($mx0 - $ot_halo - $ot_cx0) > 5.0}]
  set right_ok [expr {($ot_cx1 - $mx1 - $ot_halo) > 5.0}]
  set ot_k(L) 0; set ot_k(R) 0
  foreach it [$ot_m getITerms] {
    if {![string match "rd_out*" [[$it getMTerm] getName]]} continue
    set net [$it getNet]
    if {$net eq "NULL" || $net eq ""} continue
    set ff ""
    set nsink 0
    foreach s [$net getITerms] {
      if {$s eq $it} continue
      incr nsink
      if {[string match "DFF*" [[[$s getInst] getMaster] getName]] && [[$s getMTerm] getName] eq "D"} { set ff [$s getInst] }
    }
    if {$ff eq "" || $nsink != 1} continue
    set xy [$it getAvgXY]
    set px [expr {double([lindex $xy 1]) / $ot_dbu}]
    set py [expr {double([lindex $xy 2]) / $ot_dbu}]
    set side [expr {$px < ($mx0 + $mx1) / 2.0 ? "L" : "R"}]
    set dy 0.0
    if {$side eq "L" && !$left_ok} { set side R; set dy 16.0; incr ot_far }
    if {$side eq "R" && !$right_ok} { set side L; set dy 16.0; incr ot_far }
    set col [expr {$ot_k($side) % 4}]; incr ot_k($side)
    set w [expr {double([[$ff getMaster] getWidth]) / $ot_dbu}]
    if {$side eq "L"} {
      set x [expr {$mx0 - $ot_halo - $ot_gap - ($col + 1) * ($w + 0.2)}]
    } else {
      set x [expr {$mx1 + $ot_halo + $ot_gap + $col * ($w + 0.2)}]
    }
    $ff setLocation [expr {round($x * $ot_dbu)}] [expr {round(($py + $dy) * $ot_dbu)}]
    $ff setPlacementStatus FIRM
    lappend ot_list [$ff getName]
    incr ot_n
  }
}
# OT_PREQ=1 (el1011-q-tile 2026-10-11, RTL MPR=1): also put every per-macro request register (sole driver of a ce_in /
# addr_in pin net whose only sink is that pin) at its macro pin, same side rules.  Default off: older netlists unchanged.
set ot_nq 0
if {[info exists ::env(OT_PREQ)] && $::env(OT_PREQ) eq "1"} {
  foreach ot_m [$ot_blk getInsts] {
    if {![[$ot_m getMaster] isBlock]} continue
    if {![string match "ot_rom_*" [[$ot_m getMaster] getName]]} continue
    set b [$ot_m getBBox]
    set mx0 [expr {double([$b xMin]) / $ot_dbu}]; set mx1 [expr {double([$b xMax]) / $ot_dbu}]
    set left_ok  [expr {($mx0 - $ot_halo - $ot_cx0) > 5.0}]
    set right_ok [expr {($ot_cx1 - $mx1 - $ot_halo) > 5.0}]
    set ot_q(L) 0; set ot_q(R) 0
    foreach it [$ot_m getITerms] {
      set pn [[$it getMTerm] getName]
      if {![string match "ce_in*" $pn] && ![string match "addr_in*" $pn]} continue
      set net [$it getNet]
      if {$net eq "NULL" || $net eq ""} continue
      # the driver: the request flop itself, or the INV / BUF on its QN (ASAP7 flops have QN only) with the flop behind it
      set ff ""; set nother 0; set drv ""
      foreach s [$net getITerms] {
        if {$s eq $it} continue
        if {[$s isOutputSignal]} { set drv [$s getInst] } else { incr nother }
      }
      if {$drv eq "" || $nother != 0} continue
      set chain {}
      set dm [[$drv getMaster] getName]
      if {[string match "*DFF*" $dm]} {
        set chain [list $drv]
      } elseif {[string match "INV*" $dm] || [string match "BUF*" $dm]} {
        foreach ii [$drv getITerms] {
          if {![$ii isInputSignal]} continue
          set n2 [$ii getNet]
          if {$n2 eq "NULL" || $n2 eq ""} continue
          set f2 ""; set o2 0
          foreach s2 [$n2 getITerms] {
            if {$s2 eq $ii} continue
            if {[$s2 isOutputSignal] && [string match "*DFF*" [[[$s2 getInst] getMaster] getName]]} { set f2 [$s2 getInst] } else { incr o2 }
          }
          if {$f2 ne "" && $o2 == 0} { set chain [list $drv $f2] }
        }
      }
      if {![llength $chain]} continue
      set ff [lindex $chain 0]
      if {[lsearch -exact $ot_list [$ff getName]] >= 0} continue
      set xy [$it getAvgXY]
      set px [expr {double([lindex $xy 1]) / $ot_dbu}]
      set py [expr {double([lindex $xy 2]) / $ot_dbu}]
      set side [expr {$px < ($mx0 + $mx1) / 2.0 ? "L" : "R"}]
      set dy 0.0
      if {$side eq "L" && !$left_ok} { set side R; set dy 16.0 }
      if {$side eq "R" && !$right_ok} { set side L; set dy 16.0 }
      # columns beyond the 4 capture columns: a 1.6 um slot for the INV/BUF, then the flop
      set k $ot_q($side); incr ot_q($side)
      set off [expr {$ot_halo + $ot_gap + 4 * 1.5 + ($k % 2) * 3.6}]
      set ox 0.0
      foreach c $chain {
        set w [expr {double([[$c getMaster] getWidth]) / $ot_dbu}]
        if {$side eq "L"} { set x [expr {$mx0 - $off - $ox - $w}] } else { set x [expr {$mx1 + $off + $ox}] }
        set ox [expr {$ox + $w + 0.2}]
        $c setLocation [expr {round($x * $ot_dbu)}] [expr {round(($py + $dy) * $ot_dbu)}]
        $c setPlacementStatus FIRM
        lappend ot_list [$c getName]
      }
      incr ot_nq
    }
  }
  puts "OT_PREQ fixed $ot_nq ROM request flops at their macro ce/addr pins"
  if {$ot_nq == 0} { error "OT_PREQ: no per-macro request flop found (RTL MPR=1 expected)" }
}
set ot_fh [open $::env(RESULTS_DIR)/ot_rom_cap_at_pins.txt w]
foreach n $ot_list { puts $ot_fh $n }
close $ot_fh
puts "OT_PCAP fixed $ot_n ROM capture flops at their pins ($ot_far on the channel side, pin edge on the core boundary)"
if {$ot_n == 0} { error "OT_PCAP: no ROM rd_out -> DFF/D capture found (netlist changed?)" }
