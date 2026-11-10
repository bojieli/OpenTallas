# HBM-COLLECT-1 L1P-HS 11-10 (COORD: hold-safe shift lines, CA safe-by-design): one HB4xp67 hold pad on the sink side of
# every zero-logic hop (flop D or macro data input whose driver is a flop output through <=2 BUF/INV).
# Physical buffer only, so LEC-neutral. PRE_GLOBAL_PLACE hook (sourced from face_flops.tcl). Idempotent: skips when
# ot_hsp_pad_0 exists. Pads are NOT dont_touch: a dont_touch load pin makes RSZ insertBufferBeforeLoads fail hard
# (L1P-HS a1: RSZ-3006 in timing-driven GPL on lane0_ld__fq[0]). Zero-logic hops are not setup-critical, so repair has no
# reason to remove them; the routed pad count is checked after the run.
namespace eval ::ot_hs {
  proc is_seq {inst} {
    set m [$inst getMaster]
    if {[$m isBlock]} { return 0 }
    return [string match {*DFF*} [$m getName]]
  }
  proc is_bufinv {inst} {
    set n [[$inst getMaster] getName]
    return [expr {[string match {BUF*} $n] || [string match {INV*} $n] || [string match {HB*} $n]}]
  }
  proc src {net depth} {
    if {$net eq "NULL" || $net eq ""} { return "" }
    foreach it [$net getITerms] {
      if {![$it isOutputSignal]} continue
      set i [$it getInst]
      if {[is_seq $i]} { return [$i getName] }
      if {$depth < 2 && [is_bufinv $i]} {
        foreach a [$i getITerms] {
          if {[$a isInputSignal] && [[$a getMTerm] getSigType] eq "SIGNAL"} { return [src [$a getNet] [expr {$depth + 1}]] }
        }
      }
      return ""
    }
    return ""
  }
  proc hops {blk} {
    set out {}
    foreach i [$blk getInsts] {
      set m [$i getMaster]
      set seq [is_seq $i]
      set mac [$m isBlock]
      if {!$seq && !$mac} continue
      foreach it [$i getITerms] {
        if {![$it isInputSignal]} continue
        set pn [[$it getMTerm] getName]
        if {$seq && $pn ne "D"} continue
        if {$mac && [regexp -nocase {clk|ck} $pn]} continue
        set s [src [$it getNet] 0]
        if {$s ne ""} { lappend out [list $it $s] }
      }
    }
    return $out
  }
  set blk [ord::get_db_block]
  if {[$blk findInst ot_hsp_pad_0] ne "NULL"} {
    puts "OT_HS_PAD already present"
  } else {
    set mst ""
    foreach lib [[ord::get_db] getLibs] {
      set m [$lib findMaster HB4xp67_ASAP7_75t_R]
      if {$m ne "NULL"} { set mst $m; break }
    }
    if {$mst eq ""} { error "OT_HS_PAD: HB4xp67_ASAP7_75t_R master not found" }
    set k 0
    foreach h [hops $blk] {
      lassign $h it s
      set net [$it getNet]
      set sink [$it getInst]
      set nn [odb::dbNet_create $blk ot_hsp_net_$k]
      if {$nn eq "NULL" || $nn eq ""} { error "OT_HS_PAD: net name ot_hsp_net_$k exists" }
      set b [odb::dbInst_create $blk $mst ot_hsp_pad_$k]
      $it disconnect
      $it connect $nn
      [$b findITerm A] connect $net
      [$b findITerm Y] connect $nn
      lassign [$sink getLocation] x y
      $b setLocation $x $y
      $b setPlacementStatus PLACED
      incr k
    }
    puts "OT_HS_PAD inserted $k HB4xp67 hold pads on zero-logic hops"
  }
}
