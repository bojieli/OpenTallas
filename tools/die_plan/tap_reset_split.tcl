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
 proc run {} {
  global ct_taps
  set blk [ord::get_db_block]
  set minn [expr {[info exists ::env(OT_TAP_RESET_SPLIT_MIN)] ? $::env(OT_TAP_RESET_SPLIT_MIN) : 1}]
  set tapnets {}
  foreach tp $ct_taps {dict set tapnets [[lindex $tp 1] getName] 1}
  # collect sources first (the edit below adds DFFs that must not be visited)
  set srcs {}
  foreach inst [$blk getInsts] {
   set m [$inst getMaster]
   if {[$m isBlock] || ![string match DFF* [$m getName]]} continue
   set ck [clkterm $inst]
   if {$ck eq {} || [$ck getNet] eq "NULL" || ![dict exists $tapnets [[$ck getNet] getName]]} continue
   lappend srcs $inst
  }
  set nsrc 0; set ncopy 0; set nchain 0; set nsink 0
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
   if {[dict size $by] == 0} continue
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
  }
  puts "OT_TAP_RESET_SPLIT sources $nsrc copies $ncopy chain_cells $nchain sinks_repointed $nsink min_sinks $minn"
 }
}
::ot_tap_rsplit::run
