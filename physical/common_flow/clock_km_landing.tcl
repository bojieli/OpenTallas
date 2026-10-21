# Landing-ring roots + same-region reset relays on top of clock_split_km.tcl (ELEM-SHLK 2026-10-21).  Source it right
# AFTER physical/common_flow/clock_split_km.tcl (spec pre_cts_extra order).
# Why (route dsdv_sh_lk_s10gq-649101c0d, FF hold -30.08 / s10hq -21.31 at the routed die-boundary reference): the
# k-means clusters mix the ~1.4k input pin flops with the core mass, so pin flops inherit whatever insertion their core
# cluster gets: pin-flop clock arrival FF 431..518 ps (87 ps) around the median reference 454; the late ones (f_ks / rs_i /
# sq_i / vf_i / st_rg_w on clusters with a 64-68 ps root / leaf wire) fail input hold by up to 30 ps (137 of the 160
# failing D pins), and reset-relay leaves launched from one cluster into RESETN pins of another fail removal
# (fence.commits -5.7, u_sd relays -21.3 in s10hq).
# Fix (structural, no cycle, no logic change):
#  (1) LANDING RING: every input pin flop (D from an input port directly or through <= 2 buffers) within OT_CKLD_DEPTH
#      (30 um) of its face moves to a dedicated per-face segment root (<= OT_CKLD_SEG = 60 um of face; a face with
#      < OT_CKLD_MIN = 6 pin flops keeps them on their clusters): one BUFx24 at the segment centroid on the port net, so every landing flop of the tile sits on a short,
#      equal-shape tree that CTS latency-balances against the core clusters (neighbour-matched landing clock).
#  (2) SAME-REGION RESET: each reset-relay flop (*ot_rlv*) moves to the root that clocks the majority of its RESETN loads
#      (through <= 1 inverter / buffer), so relay launch and capture share one regional tree.
# Knobs (env): OT_CKLD (1), OT_CKLD_SEG (60), OT_CKLD_MIN (6), OT_CKLD_DEPTH (30), OT_CKLD_RST (1).
set ot_ckld_blk [ord::get_db_block]
proc ot_ckld_env {n d} { expr {[info exists ::env($n)] && $::env($n) ne "" ? $::env($n) : $d} }
if {[ot_ckld_env OT_CKLD 1] ne "0" && [$ot_ckld_blk findInst ot_ckld_0] eq "NULL"} {
  set seg [ot_ckld_env OT_CKLD_SEG 60.0]; set nmin [ot_ckld_env OT_CKLD_MIN 6]; set depth [ot_ckld_env OT_CKLD_DEPTH 30.0]
  set port [ot_ckld_env OT_CKKM_PORT clk]
  set u [[ord::get_db_tech] getDbUnitsPerMicron]
  set bt [$ot_ckld_blk findBTerm $port]
  if {$bt eq "NULL"} { error "CLOCK_KM_LANDING: no $port port" }
  set pnet [$bt getNet]
  set die [$ot_ckld_blk getDieArea]
  set dx0 [expr {[$die xMin] / double($u)}]; set dy0 [expr {[$die yMin] / double($u)}]
  set dx1 [expr {[$die xMax] / double($u)}]; set dy1 [expr {[$die yMax] / double($u)}]
  # sink -> root net (the k-means cluster nets hang off the port net through ot_ckkm_* buffers)
  array unset ot_ckld_net; set sinks {}
  foreach it [$pnet getITerms] {
    set inst [$it getInst]
    if {![string match ot_ckkm_* [$inst getName]] || ![$it isInputSignal]} continue
    set cn [[$inst findITerm Y] getNet]
    foreach s [$cn getITerms] { if {[$s isInputSignal]} { set ot_ckld_net([[$s getInst] getName]) $cn; lappend sinks $s } }
  }
  if {[llength $sinks] == 0} { error "CLOCK_KM_LANDING: no ot_ckkm_* cluster sinks (source clock_split_km.tcl first)" }
  proc ot_ckld_inport {net} {
    if {$net eq "NULL"} { return 0 }
    foreach b [$net getBTerms] { if {[$b getIoType] eq "INPUT"} { return 1 } }
    return 0
  }
  proc ot_ckld_driver {net} {
    foreach i [$net getITerms] { if {[$i isOutputSignal]} { return [$i getInst] } }
    return "NULL"
  }
  proc ot_ckld_isbuf {inst} { regexp {^(BUF|HB)} [[$inst getMaster] getName] }
  proc ot_ckld_pinflop {inst clkit port} {
    foreach i [$inst getITerms] {
      if {![$i isInputSignal] || $i eq $clkit} continue
      set n [$i getNet]
      if {$n eq "NULL" || [$n getSigType] eq "CLOCK" || [$n getSigType] eq "POWER" || [$n getSigType] eq "GROUND"} continue
      for {set lvl 0} {$lvl < 3} {incr lvl} {
        if {[ot_ckld_inport $n]} {
          foreach b [$n getBTerms] { if {[$b getName] eq $port} { return 0 } }
          return 1
        }
        set d [ot_ckld_driver $n]
        if {$d eq "NULL" || ![ot_ckld_isbuf $d]} break
        set a [$d findITerm A]
        if {$a eq "NULL"} break
        set n [$a getNet]
        if {$n eq "NULL"} break
      }
    }
    return 0
  }
  # (1) landing ring
  array unset ot_ckld_face
  foreach f {W E S N} { set ot_ckld_face($f) {} }
  set npf 0
  foreach s $sinks {
    set inst [$s getInst]
    if {[[$inst getMaster] isBlock]} continue
    if {![ot_ckld_pinflop $inst $s $port]} continue
    set l [$inst getLocation]
    set x [expr {[lindex $l 0] / double($u)}]; set y [expr {[lindex $l 1] / double($u)}]
    set d [list W [expr {$x - $dx0}] E [expr {$dx1 - $x}] S [expr {$y - $dy0}] N [expr {$dy1 - $y}]]
    set bf ""; set bd 1e30
    foreach {f v} $d { if {$v < $bd} { set bd $v; set bf $f } }
    if {$bd > $depth} continue
    set c [expr {($bf eq "W" || $bf eq "E") ? $y : $x}]
    lappend ot_ckld_face($bf) [list $c $x $y $s]
    incr npf
  }
  set m [[ord::get_db] findMaster BUFx24_ASAP7_75t_R]
  set nseg 0; set nmoved 0
  foreach f {W E S N} {
    set L [lsort -real -index 0 $ot_ckld_face($f)]
    set n [llength $L]
    if {$n < $nmin} { puts "CLOCK_KM_LANDING: face $f $n pin flops < $nmin, left on their clusters"; continue }
    # greedy segments along the face: a segment never spans more than seg um of face (short landing trees); a short
    # segment (< nmin sinks) still gets its own root -- leaving it on a core cluster is the skew this script removes
    set groups {}; set cur {}; set c0 ""
    for {set i 0} {$i < $n} {incr i} {
      set e [lindex $L $i]
      if {$c0 eq ""} { set c0 [lindex $e 0] }
      if {[lindex $e 0] - $c0 > $seg && [llength $cur] > 0} {
        lappend groups $cur; set cur {}; set c0 [lindex $e 0]
      }
      lappend cur $e
    }
    if {[llength $cur]} { lappend groups $cur }
    foreach g $groups {
      set sx 0.0; set sy 0.0
      foreach e $g { set sx [expr {$sx + [lindex $e 1]}]; set sy [expr {$sy + [lindex $e 2]}] }
      set cx [expr {$sx / [llength $g]}]; set cy [expr {$sy / [llength $g]}]
      set b [odb::dbInst_create $ot_ckld_blk $m ot_ckld_$nseg]
      $b setLocation [expr {int($cx * $u)}] [expr {int($cy * $u)}]; $b setPlacementStatus PLACED
      set net [odb::dbNet_create $ot_ckld_blk ot_ckld_${nseg}_clk]; $net setSigType CLOCK
      [$b findITerm A] connect $pnet; [$b findITerm Y] connect $net
      set cs [lsort -real [lmap e $g {lindex $e 0}]]
      foreach e $g { set it [lindex $e 3]; $it disconnect; $it connect $net; set ot_ckld_net([[$it getInst] getName]) $net; incr nmoved }
      puts [format "CLOCK_KM_LANDING: landing %d face %s %d pin flops along %.1f..%.1f root at (%.1f, %.1f)" $nseg $f [llength $g] \
        [lindex $cs 0] [lindex $cs end] $cx $cy]
      incr nseg
    }
  }
  puts "CLOCK_KM_LANDING: $npf face pin flops (depth <= $depth um), $nmoved moved onto $nseg landing roots"
  # (2) reset relays follow their loads
  if {[ot_ckld_env OT_CKLD_RST 1] ne "0"} {
    set nr 0; set nrm 0
    foreach s $sinks {
      set inst [$s getInst]
      if {![string match *ot_rlv* [$inst getName]]} continue
      incr nr
      array unset vote
      set front {}
      foreach i [$inst getITerms] { if {[$i isOutputSignal] && [$i getNet] ne "NULL"} { lappend front [list [$i getNet] 0] } }
      while {[llength $front]} {
        set fe [lindex $front 0]; set front [lrange $front 1 end]
        foreach i [[lindex $fe 0] getITerms] {
          if {![$i isInputSignal]} continue
          set li [$i getInst]; set ln [$li getName]
          if {[info exists ot_ckld_net($ln)]} {
            set k [[set ot_ckld_net($ln)] getName]
            if {[info exists vote($k)]} { incr vote($k) } else { set vote($k) 1 }
          } elseif {[lindex $fe 1] == 0 && [regexp {^(INV|BUF|HB)} [[$li getMaster] getName]]} {
            foreach o [$li getITerms] { if {[$o isOutputSignal] && [$o getNet] ne "NULL"} { lappend front [list [$o getNet] 1] } }
          }
        }
      }
      set best ""; set bv 0
      foreach k [array names vote] { if {$vote($k) > $bv} { set bv $vote($k); set best $k } }
      set cur [[set ot_ckld_net([$inst getName])] getName]
      if {$best ne "" && $best ne $cur} {
        set net [$ot_ckld_blk findNet $best]
        $s disconnect; $s connect $net; set ot_ckld_net([$inst getName]) $net; incr nrm
      }
    }
    puts "CLOCK_KM_LANDING: $nr reset-relay flops, $nrm moved to the root of their load majority"
  }
  detailed_placement
}
