# core_density_taps.tcl -- PRE_CTS hook (HBM-CLKSTRUCT 2026-10-25): structured in-core clock for single-port hard
# cores = clock port -> balanced trunk (CTS on the port net, K tap sinks) -> K DENSITY TAPS -> one local CTS tree per
# tap.  Owner decision 5 / 10-23 industry MSCTS: ~1,000-1,500 sinks per tap, taps at the sink-density medoid (always a
# legal logic site, never on a macro), each macro clock pin on the tap of its own interface registers (nearest tap).
# Replaces the single-root TritonCTS H-tree over the whole core bbox, whose branch points fall on the SRAMs, get
# legalised to the macro edges and leave 100-um leaf fans across the macros (hfd_ep_static 383..679 ps FF, adjacent
# flop pairs 212 ps apart).
# env: OT_DTAP_TARGET (max sinks per tap, default 1250), OT_DTAP_DMAX_UM (max tap region side, robust 2-98%, default 80;
#      ASAP7 placement-RC wire delay grows ~quadratically, so long strips are split), OT_DTAP_MIN (no split below 2x, default 150),
#      OT_DTAP_CELL (default BUFx24_ASAP7_75t_R), OT_DTAP_PORT (default clk), OT_DTAP_OUT (optional report file)
#      OT_DTAP_MACRO_GROUP=1 (opt-in, CLOCK-RESET S2 10-25): every hard macro + ALL its interface registers (on a macro
#        signal pin directly or through one BUF/INV, within DMAX of the macro) get ONE dedicated tap, so the macro CK
#        and its IF registers share one local tree (TritonCTS macro/register balance inside that tree).
#      OT_DTAP_MACRO_SPLIT=1 (opt-in, CLOCK-RESET S1 10-25): a tap region never straddles a macro (sinks on both sides of
#        a macro within its span are split at the macro), so no local leaf net is routed across a macro.
uplevel #0 {
set dt_blk [ord::get_db_block]
set dt_u [$dt_blk getDbUnitsPerMicron]
set dt_target [expr {[info exists ::env(OT_DTAP_TARGET)] ? $::env(OT_DTAP_TARGET) : 1250}]
set dt_dmax [expr {([info exists ::env(OT_DTAP_DMAX_UM)] ? $::env(OT_DTAP_DMAX_UM) : 80) * $dt_u}]
set dt_min [expr {[info exists ::env(OT_DTAP_MIN)] ? $::env(OT_DTAP_MIN) : 150}]
set dt_cell [expr {[info exists ::env(OT_DTAP_CELL)] ? $::env(OT_DTAP_CELL) : "BUFx24_ASAP7_75t_R"}]
set dt_port [expr {[info exists ::env(OT_DTAP_PORT)] ? $::env(OT_DTAP_PORT) : "clk"}]
set dt_master [[ord::get_db] findMaster $dt_cell]
set dt_root [[$dt_blk findBTerm $dt_port] getNet]
# sinks: {x y iterm} ; macros separately
set dt_ff {}; set dt_mac {}
foreach it [$dt_root getITerms] {
  if {[$it isOutputSignal]} continue
  set bb [$it getBBox]
  set x [expr {([$bb xMin] + [$bb xMax]) / 2}]; set y [expr {([$bb yMin] + [$bb yMax]) / 2}]
  if {[[[$it getInst] getMaster] isBlock]} { lappend dt_mac [list $x $y $it] } else { lappend dt_ff [list $x $y $it] }
}
proc dt_ext {v} {
  # robust extent (2nd..98th percentile) so a few stray sinks never force a split
  set n [llength $v]; set lo [lindex $v [expr {int(0.02 * ($n - 1))}]]; set hi [lindex $v [expr {int(0.98 * ($n - 1))}]]
  return [expr {$hi - $lo}]
}
set dt_mgrp_on [expr {[info exists ::env(OT_DTAP_MACRO_GROUP)] && $::env(OT_DTAP_MACRO_GROUP) eq "1"}]
set dt_msplit_on [expr {[info exists ::env(OT_DTAP_MACRO_SPLIT)] && $::env(OT_DTAP_MACRO_SPLIT) eq "1"}]
set dt_mbox {}
foreach p $dt_mac { set bb [[[lindex $p 2] getInst] getBBox]; lappend dt_mbox [list [$bb xMin] [$bb yMin] [$bb xMax] [$bb yMax]] }
# macro straddle: the macro with the most sinks on BOTH sides inside its own span -> {axis cut} (empty if none)
proc dt_straddle {pts} {
  global dt_mbox
  set best {}; set bn [expr {[info exists ::env(OT_DTAP_MACRO_SPLIT_MIN)] ? $::env(OT_DTAP_MACRO_SPLIT_MIN) - 1 : 7}]
  foreach m $dt_mbox {
    lassign $m x0 y0 x1 y1
    foreach ax {0 1} lo [list $x0 $y0] hi [list $x1 $y1] olo [list $y0 $x0] ohi [list $y1 $x1] {
      set a 0; set b 0
      foreach p $pts {
        set o [lindex $p [expr {1 - $ax}]]; if {$o < $olo || $o > $ohi} continue
        set v [lindex $p $ax]; if {$v < $lo} { incr a } elseif {$v > $hi} { incr b }
      }
      set n [expr {min($a, $b)}]
      if {$n > $bn} { set bn $n; set best [list $ax [expr {($lo + $hi) / 2}]] }   ;# >= MIN (default 8) sinks each side
    }
  }
  return $best
}
proc dt_split {pts} {
  global dt_target dt_dmax dt_min
  set n [llength $pts]
  set xs [lsort -integer [lmap p $pts {lindex $p 0}]]; set ys [lsort -integer [lmap p $pts {lindex $p 1}]]
  set w [dt_ext $xs]; set h [dt_ext $ys]
  # leaf: within the sink cap and DMAX in BOTH directions (no small-set exception: f790 v3e tap 10 = 129 W-face flops
  # over 193 um behind the SRAM column, one leaf tree 577..753 ps -> dout -> pin_flit hold -140 ps); only a handful of
  # sinks (< 16) may form a leaf beyond DMAX
  if {$::dt_msplit_on && $n > 1} {
    set st [dt_straddle $pts]
    if {[llength $st]} {
      lassign $st ax cut; set A {}; set B {}
      foreach p $pts { if {[lindex $p $ax] < $cut} { lappend A $p } else { lappend B $p } }
      return [concat [dt_split $A] [dt_split $B]]
    }
  }
  if {$n <= $dt_target && (($w <= $dt_dmax && $h <= $dt_dmax) || $n < 16)} { return [list $pts] }
  # count-median bisection along the longer side (weighted-median bisection, taps.py density_taps)
  set ax [expr {$w >= $h ? 0 : 1}]
  set s [lsort -integer -index $ax $pts]
  set m [expr {$n / 2}]
  return [concat [dt_split [lrange $s 0 [expr {$m - 1}]]] [dt_split [lrange $s $m end]]]
}
# S2 macro groups: interface registers of every macro (direct or through one BUF/INV on a macro signal pin, within
# DMAX of the macro bbox) -> one dedicated set per macro; a register on several macros goes to the one it touches most
set dt_mgrp [dict create]; set dt_mset {}
if {$dt_mgrp_on} {
  set dt_ffi [dict create]
  foreach p $dt_ff { dict set dt_ffi [[[lindex $p 2] getInst] getName] $p }
  proc dt_if_regs {net depth} {
    global dt_ffi
    set out {}
    foreach it [$net getITerms] {
      set i [$it getInst]; set nm [$i getName]
      if {[dict exists $dt_ffi $nm]} { lappend out $nm; continue }
      if {$depth > 0 && [regexp {^(BUF|INV|HB)} [[$i getMaster] getName]]} {
        foreach o [$i getITerms] {
          set on [$o getNet]
          if {$on eq "NULL" || $on eq "" || $on eq $net || [$on getSigType] ne "SIGNAL"} continue
          lappend out {*}[dt_if_regs $on 0]
        }
      }
    }
    return $out
  }
  set dt_rc [dict create]
  set k 0
  foreach p $dt_mac {
    set mi [[lindex $p 2] getInst]; lassign [lindex $dt_mbox $k] x0 y0 x1 y1
    foreach t [$mi getITerms] {
      set n [$t getNet]
      if {$n eq "NULL" || $n eq "" || [$n getSigType] ne "SIGNAL"} continue
      foreach r [dt_if_regs $n 1] {
        set q [dict get $dt_ffi $r]; set qx [lindex $q 0]; set qy [lindex $q 1]
        set dx [expr {$qx < $x0 ? $x0 - $qx : ($qx > $x1 ? $qx - $x1 : 0)}]; set dy [expr {$qy < $y0 ? $y0 - $qy : ($qy > $y1 ? $qy - $y1 : 0)}]
        if {$dx + $dy > $dt_dmax} continue
        dict set dt_rc $r $k [expr {[dict exists $dt_rc $r $k] ? [dict get $dt_rc $r $k] + 1 : 1}]
      }
    }
    incr k
  }
  dict for {r cs} $dt_rc {
    set bk ""; set bc 0
    dict for {k c} $cs { if {$c > $bc} { set bc $c; set bk $k } }
    dict set dt_mgrp $r $bk
  }
  set rest {}
  foreach p $dt_ff { if {![dict exists $dt_mgrp [[[lindex $p 2] getInst] getName]]} { lappend rest $p } }
  set dt_ff_all $dt_ff; set dt_ff $rest
}
set dt_sets [dt_split $dt_ff]
# set index -> macro index for the S2 macro groups (each macro with >= 1 interface register)
set dt_set_mac [dict create]
if {$dt_mgrp_on} {
  for {set k 0} {$k < [llength $dt_mac]} {incr k} {
    set S {}
    foreach p $dt_ff_all { set nm [[[lindex $p 2] getInst] getName]; if {[dict exists $dt_mgrp $nm] && [dict get $dt_mgrp $nm] == $k} { lappend S $p } }
    if {![llength $S]} continue
    dict set dt_set_mac [llength $dt_sets] $k
    lappend dt_sets $S
  }
  set dt_ff $dt_ff_all
}
set dt_taps {}
set dt_of [dict create]
# medoid of every set: the sink nearest the set centroid (a placed register = legal logic area, never on a macro)
set dt_med {}
foreach S $dt_sets {
  set n [llength $S]; set cx 0.0; set cy 0.0
  foreach p $S { set cx [expr {$cx + [lindex $p 0]}]; set cy [expr {$cy + [lindex $p 1]}] }
  set cx [expr {$cx / $n}]; set cy [expr {$cy / $n}]
  set best ""; set bd 1e30
  foreach p $S { set d [expr {abs([lindex $p 0] - $cx) + abs([lindex $p 1] - $cy)}]; if {$d < $bd} { set bd $d; set best $p } }
  lappend dt_med [list [lindex $best 0] [lindex $best 1]]
}
# stray sinks (the robust split ignores the outer 2%): a sink farther than DMAX from its own tap joins the nearest tap
set dt_moved 0
array unset dt_asg
for {set k 0} {$k < [llength $dt_sets]} {incr k} { set dt_asg($k) {} }
set k 0
foreach S $dt_sets {
  lassign [lindex $dt_med $k] mx my
  foreach p $S {
    set t $k
    if {![dict exists $dt_set_mac $k] && abs([lindex $p 0] - $mx) + abs([lindex $p 1] - $my) > $dt_dmax} {
      set bd 1e30
      for {set j 0} {$j < [llength $dt_med]} {incr j} {
        lassign [lindex $dt_med $j] qx qy
        set d [expr {abs([lindex $p 0] - $qx) + abs([lindex $p 1] - $qy)}]
        if {$d < $bd} { set bd $d; set t $j }
      }
      if {$t != $k} { incr dt_moved }
    }
    lappend dt_asg($t) $p
  }
  incr k
}
# F4 (QC cqb GEOM 10-25): zero-logic register pairs (Q -> D directly or through one BUF/INV: face-shell pin register
# -> core register, SRAM dout capture -> pin_flit) have ~15-20 ps of data delay, less than any inter-tap skew; the
# capture register joins the launch register's tap when they sit within DMAX/2 of each other.
set dt_pt [dict create]; set dt_tp [dict create]
for {set k 0} {$k < [llength $dt_sets]} {incr k} {
  foreach p $dt_asg($k) { set nm [[[lindex $p 2] getInst] getName]; dict set dt_pt $nm $p; dict set dt_tp $nm $k }
}
proc dt_d_sinks {net depth} {
  set out {}
  foreach it [$net getITerms] {
    if {![$it isInputSignal]} continue
    set i [$it getInst]; set mn [[$i getMaster] getName]
    if {[string match "*DFF*" $mn] && [string match "D*" [[$it getMTerm] getName]]} { lappend out [$i getName]; continue }
    if {$depth > 0 && [regexp {^(BUF|INV)} $mn]} {
      foreach o [$i getITerms] {
        if {[$o isOutputSignal] && [$o getNet] ne "NULL" && [$o getNet] ne ""} { lappend out {*}[dt_d_sinks [$o getNet] 0] }
      }
    }
  }
  return $out
}
set dt_f4 0
dict for {nm p} $dt_pt {
  set t [dict get $dt_tp $nm]
  foreach o [[[lindex $p 2] getInst] getITerms] {
    if {![$o isOutputSignal]} continue
    set n [$o getNet]; if {$n eq "NULL" || $n eq ""} continue
    if {[$n getSigType] ne "SIGNAL"} continue
    foreach c [dt_d_sinks $n 1] {
      if {![dict exists $dt_tp $c] || [dict get $dt_tp $c] == $t || [dict exists $dt_mgrp $c]} continue
      set q [dict get $dt_pt $c]
      if {abs([lindex $q 0] - [lindex $p 0]) + abs([lindex $q 1] - [lindex $p 1]) > $dt_dmax / 2} continue
      dict set dt_tp $c $t; incr dt_f4
    }
  }
}
array unset dt_asg
for {set k 0} {$k < [llength $dt_sets]} {incr k} { set dt_asg($k) {} }
dict for {nm p} $dt_pt { lappend dt_asg([dict get $dt_tp $nm]) $p }
for {set k 0} {$k < [llength $dt_sets]} {incr k} {
  set S $dt_asg($k)
  if {![llength $S]} continue
  lassign [lindex $dt_med $k] mx my
  set inst [odb::dbInst_create $dt_blk $dt_master "ot_dtap_$k"]
  $inst setLocation $mx $my
  $inst setPlacementStatus PLACED
  set net [odb::dbNet_create $dt_blk "ot_dtap_net_$k"]
  $net setSigType CLOCK
  foreach mt [$dt_master getMTerms] {
    if {[$mt getSigType] ne "SIGNAL"} continue
    if {[$mt getIoType] eq "INPUT"} { [$inst findITerm [$mt getName]] connect $dt_root } else { [$inst findITerm [$mt getName]] connect $net }
  }
  foreach p $S { set it [lindex $p 2]; dict set dt_of [[$it getInst] getName] $k; $it disconnect; $it connect $net }
  lappend dt_taps [list $k $mx $my $net [llength $S]]
}
# macro clock pins -> the tap of the macro's own interface registers (F3: macro clock pin + its wd/addr/ctl and rd
# capture registers in one sub-tree): the tap owning most registers wired directly (or through one buffer/inverter)
# to the macro's signal pins; the nearest tap only if no interface register is found.
proc dt_regs_on {net depth} {
  global dt_of
  set out {}
  foreach it [$net getITerms] {
    set i [$it getInst]; set nm [$i getName]
    if {[dict exists $dt_of $nm]} { lappend out [dict get $dt_of $nm]; continue }
    if {$depth > 0 && [regexp {^(BUF|INV|HB)} [[$i getMaster] getName]]} {
      foreach o [$i getITerms] {
        if {[$o isOutputSignal] && [$o getNet] ne "NULL" && [$o getNet] ne ""} { lappend out {*}[dt_regs_on [$o getNet] 0] }
        if {[$o isInputSignal] && [$o getNet] ne "NULL" && [$o getNet] ne "" && [$o getNet] ne $net} { lappend out {*}[dt_regs_on [$o getNet] 0] }
      }
    }
  }
  return $out
}
set dt_mrep {}
foreach p $dt_mac {
  lassign $p x y it
  set cnt [dict create]
  foreach mi [[$it getInst] getITerms] {
    set n [$mi getNet]
    if {$n eq "NULL" || $n eq "" || [$n getSigType] ne "SIGNAL"} continue
    foreach t [dt_regs_on $n 1] { dict incr cnt $t }
  }
  set bt ""; set bc 0
  dict for {t c} $cnt {
    set tt [lindex $dt_taps [lsearch -exact -index 0 $dt_taps $t]]
    if {abs([lindex $tt 1] - $x) + abs([lindex $tt 2] - $y) > 1.5 * $dt_dmax} continue
    if {$c > $bc} { set bc $c; set bt $t }
  }
  set how "interface regs $bc"
  set mk [lsearch -exact $dt_mac $p]
  dict for {si mi} $dt_set_mac { if {$mi == $mk} { set bt $si; set how "macro group tap (S2)" } }
  if {$bt eq ""} {
    set bd 1e30; set how nearest
    foreach t $dt_taps { set d [expr {abs([lindex $t 1] - $x) + abs([lindex $t 2] - $y)}]; if {$d < $bd} { set bd $d; set bt [lindex $t 0] } }
  }
  set tt [lindex $dt_taps [lsearch -exact -index 0 $dt_taps $bt]]
  set dd [expr {(abs([lindex $tt 1] - $x) + abs([lindex $tt 2] - $y)) / double($dt_u)}]
  $it disconnect; $it connect [lindex $tt 3]
  lappend dt_mrep "[[$it getInst] getName] -> ot_dtap_$bt ($how, [format %.1f $dd] um)"
}
detailed_placement
set dt_lines {}
foreach t $dt_taps {
  set i [$dt_blk findInst "ot_dtap_[lindex $t 0]"]; lassign [$i getLocation] lx ly
  lappend dt_lines [format "OT_DTAP tap %d sinks %d at %.2f %.2f um (medoid %.2f %.2f)" [lindex $t 0] [lindex $t 4] [expr {$lx / double($dt_u)}] [expr {$ly / double($dt_u)}] [expr {[lindex $t 1] / double($dt_u)}] [expr {[lindex $t 2] / double($dt_u)}]]
}
foreach l $dt_lines { puts $l }
foreach l $dt_mrep { puts "OT_DTAP macro $l" }
puts "OT_DTAP S2 macro groups [dict size $dt_set_mac] ([dict size $dt_mgrp] interface regs), macro split $dt_msplit_on"
puts "OT_DTAP done: $dt_moved stray sinks re-homed; $dt_f4 zero-logic capture regs joined their launch tap (F4); [llength $dt_taps] density taps for [llength $dt_ff] register sinks (target $dt_target/tap), [llength $dt_mac] macro clock pins on nearest tap"
if {[info exists ::env(OT_DTAP_OUT)]} { set fh [open $::env(OT_DTAP_OUT) w]; puts $fh [join [concat $dt_lines $dt_mrep] "\n"]; close $fh }
}
