# QC-COLL RST-COTAP 11-22 (OPUS-FIX-QC-COLL-R3, COORD: "each reset synchroniser on the same clock tap as its loads"; opt-in
# OT_TAP_RESET_SPLIT=1 from plan clock.tap_reset_split, unset = no-op).  Sourced from clock_taps.tcl right after
# tap_reset_affinity.tcl (which already moved each last reset stage onto the tap that holds MOST of its async sinks).
# Why: a last reset stage whose async RESETN/SETN sinks sit on SEVERAL taps keeps a tap-to-tap removal path to every sink
# on another tap (qwen_compute coll_core v2 proof: 34 sources, 675 sinks on another tap, 606 of them left by the affinity
# pass; worst u_wreset.sync_rst_n clk_t67 -> seen[10] clk_t77 removal -76.78 ps at CTS; u_rsp/q drives 241 sinks on 10 taps).
# What: for every such source S (a DFF whose outputs reach, through INV/BUF/CKINV/HB cells (depth <= 4), async pins on at least
# 2 flops, with async loads >= other loads -- the tap_reset_affinity.tcl rule), and every OTHER tap T that holds some of its
# async sinks: one copy S_rtap<T> of S (same master, same D / RESETN / SETN nets, CLK on tap T) plus copies of the
# INV/BUF chain cells on the way, so each sink keeps its exact polarity and stage count (latency equal, same function:
# the copy is the same register clocked by the same clock, only from the sink's own tap).  Each copy is placed at the
# centroid of the sinks it now drives (PLACED; the post-CTS detailed_placement legalizes it).  A tap with fewer than
# OT_TAP_RESET_SPLIT_MIN (default 1) sinks of S is left alone.  Clock pin of S itself is not touched here.
# LEC: same-side duplicate registers (lec.py proposes them by next-state identity).  Reports one line OT_TAP_RESET_SPLIT.
namespace eval ::ot_tap_rsplit {
 # sinks: list of {async_iterm chain} where chain = list of INV/BUF insts from S's output net to the sink pin
 proc fwd {net depth chain} {
  set out {}; set other 0
  foreach it [$net getITerms] {
   if {![$it isInputSignal]} continue
   set inst [$it getInst]; set m [$inst getMaster]; set mn [$m getName]; set pin [[$it getMTerm] getName]
   if {[$m isBlock]} {incr other; continue}
   if {[string match DFF* $mn] && ($pin eq "RESETN" || $pin eq "SETN")} {lappend out [list $it $chain]; continue}
   if {$depth < 4 && ([string match INV* $mn] || [string match BUF* $mn] || [string match CKINV* $mn] || [string match HB* $mn])} {
    foreach o [$inst getITerms] {
     if {[$o isOutputSignal] && [$o getNet] ne "NULL"} {
      lassign [fwd [$o getNet] [expr {$depth+1}] [concat $chain [list $inst]]] a b
      set out [concat $out $a]; incr other $b
     }
    }
    continue
   }
   incr other
  }
  return [list $out $other]
 }
 proc clkterm {inst} {
  foreach it [$inst getITerms] {if {[[$it getMTerm] getName] in {CLK CLKN}} {return $it}}
  return {}
 }
 proc outterm {inst} {
  foreach it [$inst getITerms] {if {[$it isOutputSignal] && [$it getNet] ne "NULL"} {return $it}}
  return {}
 }
 proc uniq {blk base} {
  set n $base; set k 0
  while {[$blk findInst $n] ne "NULL" || [$blk findNet $n] ne "NULL"} {incr k; set n ${base}_$k}
  return $n
 }
 # QC-COLL RST-LAUNCH 11-23 (opt-in OT_TAP_RESET_SPLIT_LAUNCH=1 from clock.tap_reset_split_launch; COORD: hold gets a
 # structural fix, a retimed launch).  coll_core pkit_core4 CTS: u_rx.u_wreset.reset_pipe[0] (source tap) ->
 # sync_rst_n_rtap_clk_t68 hold -112.9 ps (skew 147): the affinity move / per-tap copy put the LAST stage on its sinks' tap
 # but left the stage(s) before it on the old tap, i.e. a zero-logic tap-to-tap shift.  For every moved or copied last
 # stage X on tap T: walk D back through INV/BUF/HB (depth <= 4) to the launching DFF L; when L is not on T, put L on T as
 # well (a copy L_rtap_<T> with the same master, every non-clock input net of L, its INV/BUF chain copied), and repeat
 # for the copy's own D up to OT_TAP_RESET_SPLIT_LAUNCH_DEPTH (default 3) stages, stopping at a DFF whose D is a TIE cell
 # (the synchroniser's first stage).  A source X whose launcher drives only X has the launcher's own clock pin moved to T
 # (no copy).  Same function: each stage is the same register on the same clock from another tap (async assert unchanged,
 # deassert edge count unchanged).  LEC: <src>_rtap_<tap> duplicate registers (lec.py TAP_CLONE).
 proc back {net depth} {
  # driver of net -> {dff chain} with chain = INV/BUF insts from the dff output toward net (dff output first)
  if {$net eq "NULL"} {return {}}
  foreach it [$net getITerms] {
   if {![$it isOutputSignal]} continue
   set inst [$it getInst]; set mn [[$inst getMaster] getName]
   if {[string match DFF* $mn]} {return [list $inst $it {}]}
   if {$depth < 4 && ([string match INV* $mn] || [string match BUF* $mn] || [string match HB* $mn])} {
    foreach i [$inst getITerms] {
     if {[$i isInputSignal] && [$i getNet] ne "NULL" && ![[$i getNet] isSpecial]} {
      set r [back [$i getNet] [expr {$depth+1}]]
      if {$r eq {}} {return {}}
      lassign $r d o ch
      return [list $d $o [concat $ch [list $inst]]]
     }
    }
   }
   return {}
  }
  return {}
 }
 proc const_d {inst} {
  set d [$inst findITerm D]
  if {$d eq "NULL" || [$d getNet] eq "NULL"} {return 0}
  foreach it [[$d getNet] getITerms] {
   if {[$it isOutputSignal] && [string match TIE* [[[$it getInst] getMaster] getName]]} {return 1}
  }
  return 0
 }
 proc nloads {net} {
  set n 0
  foreach it [$net getITerms] {if {[$it isInputSignal]} {incr n}}
  return [expr {$n + [llength [$net getBTerms]]}]
 }
 proc launch {blk x t depth maxd} {
  variable lmemo; variable lstat
  set dit [$x findITerm D]
  if {$dit eq "NULL" || [$dit getNet] eq "NULL"} return
  set r [back [$dit getNet] 0]
  if {$r eq {}} return
  lassign $r l lo chain
  set lck [clkterm $l]
  if {$lck eq {} || [$lck getNet] eq "NULL"} return
  if {[[$lck getNet] getName] eq $t} return
  set key "[$l getName]|$t"
  if {[dict exists $lmemo $key]} {$dit disconnect; $dit connect [dict get $lmemo $key]; dict incr lstat reuse; return}
  # LEP-RSPLIT-CAP-1 (HEAD-R18 11-23, opt-in OT_TAP_RESET_SPLIT_MAX_TAPS from clock.tap_reset_split_max_taps; unset/0 = no
  # cap, byte-identical): a launcher already present on MAX_TAPS taps (its own + copies) gets no further copy.  HEAD E cap10:
  # uncapped launch copied the ot_rst_fan root (root_r) onto every tap of its leaves, so the relay feeding it (u_rrl_303)
  # was split onto 175 taps and its AND-gated D net drove 175 loads (TT -2690.91 ps, 2541 ps wire).  Capped, the fan tree
  # keeps its own registered hops (2/4/6 branches) and the tap-to-tap stage stays at this boundary (counted capped).
  variable maxt; variable ltaps
  if {$maxt > 0} {
   set ln [$l getName]
   if {![dict exists $ltaps $ln]} {dict set ltaps $ln [list [[$lck getNet] getName]]}
   if {[llength [dict get $ltaps $ln]] >= $maxt} {dict incr lstat capped; return}
   dict lappend ltaps $ln $t
  }
  # launcher driving only X (single chain, single load each): move its clock pin, no copy
  set solo [expr {[nloads [$lo getNet]] == 1}]
  foreach ci $chain {if {[nloads [[outterm $ci] getNet]] != 1} {set solo 0}}
  if {$solo} {
   $lck disconnect; $lck connect [$blk findNet $t]; dict incr lstat moved
   dict set lmemo $key [$dit getNet]
   if {![const_d $l] && $depth < $maxd} {launch $blk $l $t [expr {$depth+1}] $maxd} elseif {![const_d $l]} {dict incr lstat unresolved}
   return
  }
  set b [$x getBBox]; set cx [$b xMin]; set cy [$b yMin]
  set cn [uniq $blk "[$l getName]_rtap_$t"]
  set c [odb::dbInst_create $blk [$l getMaster] $cn]
  foreach it [$l getITerms] {
   set mt [[$it getMTerm] getName]
   if {[$it isOutputSignal] || $mt in {CLK CLKN}} continue
   if {[$it getNet] ne "NULL"} {[$c findITerm $mt] connect [$it getNet]}
  }
  [$c findITerm [[$lck getMTerm] getName]] connect [$blk findNet $t]
  set drv [odb::dbNet_create $blk [uniq $blk "${cn}_q"]]
  [$c findITerm [[$lo getMTerm] getName]] connect $drv
  $c setLocation $cx $cy; $c setPlacementStatus PLACED
  dict incr lstat copies
  foreach ci $chain {
   set nn [uniq $blk "[$ci getName]_rtap_$t"]
   set cc [odb::dbInst_create $blk [$ci getMaster] $nn]
   foreach it [$ci getITerms] {
    if {[$it isInputSignal] && [$it getNet] ne "NULL" && ![[$it getNet] isSpecial]} {[$cc findITerm [[$it getMTerm] getName]] connect $drv}
   }
   set on [odb::dbNet_create $blk [uniq $blk "${nn}_y"]]
   [$cc findITerm [[[outterm $ci] getMTerm] getName]] connect $on
   $cc setLocation $cx $cy; $cc setPlacementStatus PLACED
   set drv $on; dict incr lstat chain
  }
  $dit disconnect; $dit connect $drv
  dict set lmemo $key $drv
  if {![const_d $l] && $depth < $maxd} {launch $blk $c $t [expr {$depth+1}] $maxd} elseif {![const_d $l]} {dict incr lstat unresolved}
 }
 proc run {} {
  global ct_taps
  set blk [ord::get_db_block]
  set minn [expr {[info exists ::env(OT_TAP_RESET_SPLIT_MIN)] ? $::env(OT_TAP_RESET_SPLIT_MIN) : 1}]
  set ldo [expr {[info exists ::env(OT_TAP_RESET_SPLIT_LAUNCH)] && $::env(OT_TAP_RESET_SPLIT_LAUNCH) eq "1"}]
  set maxd [expr {[info exists ::env(OT_TAP_RESET_SPLIT_LAUNCH_DEPTH)] ? $::env(OT_TAP_RESET_SPLIT_LAUNCH_DEPTH) : 3}]
  variable lmemo {}; variable lstat {}; set nlsrc 0
  variable maxt [expr {[info exists ::env(OT_TAP_RESET_SPLIT_MAX_TAPS)] ? $::env(OT_TAP_RESET_SPLIT_MAX_TAPS) : 0}]
  variable ltaps {}; set ncapped 0
  set tapnets {}
  foreach tp $ct_taps {dict set tapnets [[lindex $tp 1] getName] 1}
  # RST-LAUNCH rounds (COORD 11-23 04:xx: pkit_core5a launch=0 31 split sources, launch=1 32): a launch copy / moved launcher is a
  # NEW async sink of the reset source that drives its RESETN/SETN (u_rrl_340 gained sinks on 11 taps, u_rrl_234 on 6).  Run
  # inline, the launch pass let a parent visited AFTER it see those sinks and a parent visited BEFORE it miss them (order bug).
  # A split also adds async sinks without a launch change: HEAD LEP region root copies turned one upstream reset load
  # into 65. Iterate until neither pass changes the reset network (OT_TAP_RESET_SPLIT_ROUNDS, default 4).
  # Without the launch pass: one round, as before.
  set maxr [expr {$ldo ? ([info exists ::env(OT_TAP_RESET_SPLIT_ROUNDS)] ? $::env(OT_TAP_RESET_SPLIT_ROUNDS) : 4) : 1}]
  set nsrc 0; set ncopy 0; set nchain 0; set nsink 0; set nround 0; set converged [expr {!$ldo}]
  for {set round 1} {$round <= $maxr} {incr round} {
  incr nround; set pend {}; set copies_at_start $ncopy
  # collect sources first (the edit below adds DFFs that must not be visited)
  set srcs {}
  foreach inst [$blk getInsts] {
   set m [$inst getMaster]
   if {[$m isBlock] || ![string match DFF* [$m getName]]} continue
   set ck [clkterm $inst]
   if {$ck eq {} || [$ck getNet] eq "NULL" || ![dict exists $tapnets [[$ck getNet] getName]]} continue
   lappend srcs $inst
  }
  foreach inst $srcs {
   set ck [clkterm $inst]; set stap [[$ck getNet] getName]
   set out {}; set other 0
   foreach it [$inst getITerms] {
    if {[$it isOutputSignal] && [$it getNet] ne "NULL"} {lassign [fwd [$it getNet] 0 {}] a b; set out [concat $out $a]; incr other $b}
   }
   if {[llength $out] < 2 || [llength $out] < $other} continue
   # group sinks by their tap
   set by {}
   foreach s $out {
    lassign $s a chain
    set sck [clkterm [$a getInst]]
    if {$sck eq {} || [$sck getNet] eq "NULL"} continue
    set t [[$sck getNet] getName]
    if {$t eq $stap || ![dict exists $tapnets $t]} continue
    dict lappend by $t $s
   }
   set clones {}
   # LEP-RSPLIT-CAP-1: same cap on the per-tap source split (own tap + copies <= MAX_TAPS); a capped source is left as is
   # (treated exactly as a source with no other-tap sinks: no copy, its own launch stage still walked in launch mode)
   if {$maxt > 0 && [dict size $by] + 1 > $maxt} {incr ncapped; set by {}}
   if {[dict size $by] == 0} {
    if {$ldo} {lappend pend [list $inst $stap]}
    continue
   }
   incr nsrc
   set so [outterm $inst]; set somt [[$so getMTerm] getName]
   dict for {t sinks} $by {
    if {[llength $sinks] < $minn} continue
    # placement: centroid of the sinks of this tap
    set sx 0; set sy 0
    foreach s $sinks {set b [[[lindex $s 0] getInst] getBBox]; incr sx [expr {([$b xMin]+[$b xMax])/2}]; incr sy [expr {([$b yMin]+[$b yMax])/2}]}
    set cx [expr {$sx / [llength $sinks]}]; set cy [expr {$sy / [llength $sinks]}]
    set cn [uniq $blk "[$inst getName]_rtap_$t"]
    set c [odb::dbInst_create $blk [$inst getMaster] $cn]
    foreach it [$inst getITerms] {
     set mt [[$it getMTerm] getName]
     if {[$it isOutputSignal] || $mt in {CLK CLKN}} continue
     if {[$it getNet] ne "NULL"} {[$c findITerm $mt] connect [$it getNet]}
    }
    [$c findITerm [[$ck getMTerm] getName]] connect [$blk findNet $t]
    set cnet [odb::dbNet_create $blk [uniq $blk "${cn}_q"]]
    [$c findITerm $somt] connect $cnet
    $c setLocation $cx $cy; $c setPlacementStatus PLACED
    incr ncopy
    lappend clones [list $c $t]
    # chain copies, memo by original chain inst name -> output net of its copy for this tap
    set memo {}
    foreach s $sinks {
     lassign $s a chain
     set drv $cnet
     foreach ci $chain {
      set key [$ci getName]
      if {[dict exists $memo $key]} {set drv [dict get $memo $key]; continue}
      set nn [uniq $blk "${key}_rtap_$t"]
      set cc [odb::dbInst_create $blk [$ci getMaster] $nn]
      foreach it [$ci getITerms] {
       if {[$it isInputSignal] && [$it getNet] ne "NULL" && ![[$it getNet] isSpecial]} {[$cc findITerm [[$it getMTerm] getName]] connect $drv}
      }
      set on [odb::dbNet_create $blk [uniq $blk "${nn}_y"]]
      [$cc findITerm [[[outterm $ci] getMTerm] getName]] connect $on
      $cc setLocation $cx $cy; $cc setPlacementStatus PLACED
      dict set memo $key $on; set drv $on; incr nchain
     }
     $a disconnect; $a connect $drv; incr nsink
    }
   }
   if {$ldo} {
    foreach ct $clones {lappend pend $ct}
    lappend pend [list $inst $stap]
   }
  }
  if {!$ldo} break
  set k0 [expr {([dict exists $lstat copies] ? [dict get $lstat copies] : 0) + ([dict exists $lstat moved] ? [dict get $lstat moved] : 0)}]
  foreach pt $pend {lassign $pt x t; launch $blk $x $t 1 $maxd; incr nlsrc}
  set k1 [expr {([dict exists $lstat copies] ? [dict get $lstat copies] : 0) + ([dict exists $lstat moved] ? [dict get $lstat moved] : 0)}]
  if {$k1 == $k0 && $ncopy == $copies_at_start} {set converged 1; break}
  }
  puts "OT_TAP_RESET_SPLIT sources $nsrc copies $ncopy chain_cells $nchain sinks_repointed $nsink min_sinks $minn[expr {$maxt > 0 ? " max_taps $maxt capped_sources $ncapped" : ""}]"
  if {$ldo} {
   set g {}; foreach k [expr {$maxt > 0 ? {moved copies chain reuse unresolved capped} : {moved copies chain reuse unresolved}}] {lappend g $k [expr {[dict exists $lstat $k] ? [dict get $lstat $k] : 0}]}
   puts "OT_TAP_RESET_SPLIT_LAUNCH stages $nlsrc [join $g { }] max_depth $maxd rounds $nround converged $converged"
  }
 }
}
::ot_tap_rsplit::run
