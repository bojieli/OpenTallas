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
uplevel #0 {
set dt_blk [ord::get_db_block]
set dt_u [$dt_blk getDbUnitsPerMicron]
set dt_target [expr {[info exists ::env(OT_DTAP_TARGET)] ? $::env(OT_DTAP_TARGET) : 1250}]
set dt_dmax [expr {([info exists ::env(OT_DTAP_DMAX_UM)] ? $::env(OT_DTAP_DMAX_UM) : 80) * $dt_u}]
set dt_min [expr {[info exists ::env(OT_DTAP_MIN)] ? $::env(OT_DTAP_MIN) : 150}]
set dt_cell [expr {[info exists ::env(OT_DTAP_CELL)] ? $::env(OT_DTAP_CELL) : "BUFx24_ASAP7_75t_R"}]
set dt_port [expr {[info exists ::env(OT_DTAP_PORT)] ? $::env(OT_DTAP_PORT) : "clk"}]
set dt_master [[ord::get_db] findMaster $dt_cell]
set dt_bt [$dt_blk findBTerm $dt_port]
if {$dt_bt eq "NULL"} { error "OT_DTAP_PORT missing $dt_port" }
set dt_root [$dt_bt getNet]
if {$dt_root eq "NULL"} { error "OT_DTAP_PORT disconnected $dt_port" }
set dt_id_offset [expr {[info exists ::env(OT_DTAP_ID_OFFSET)] ? $::env(OT_DTAP_ID_OFFSET) : 0}]
set dt_layout [expr {[info exists ::env(OT_DTAP_LAYOUT)] ? $::env(OT_DTAP_LAYOUT) : "density"}]
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
proc dt_split {pts} {
  global dt_target dt_dmax dt_min dt_layout
  set n [llength $pts]
  if {!$n} { return {} }
  set xs [lsort -integer [lmap p $pts {lindex $p 0}]]; set ys [lsort -integer [lmap p $pts {lindex $p 1}]]
  set w [dt_ext $xs]; set h [dt_ext $ys]
  # leaf: within the sink cap and DMAX in BOTH directions (no small-set exception: f790 v3e tap 10 = 129 W-face flops
  # over 193 um behind the SRAM column, one leaf tree 577..753 ps -> dout -> pin_flit hold -140 ps); only a handful of
  # sinks (< 16) may form a leaf beyond DMAX
  if {$n <= $dt_target && (($w <= $dt_dmax && $h <= $dt_dmax) || $n < 16)} { return [list $pts] }
  # count-median bisection along the longer side (weighted-median bisection, taps.py density_taps)
  set ax [expr {$dt_layout eq "columns" ? ($w > $dt_dmax ? 0 : 1) : ($w >= $h ? 0 : 1)}]
  set s [lsort -integer -index $ax $pts]
  set m [expr {$n / 2}]
  return [concat [dt_split [lrange $s 0 [expr {$m - 1}]]] [dt_split [lrange $s $m end]]]
}
# A native macro-only clock keeps its own input driver. Its tap uses the nearest
# placed standard-cell site, never a point on the macro. No other root is merged.
if {![llength $dt_ff] && [llength $dt_mac]} {
  set dt_macro_sinks {}
  foreach dt_mp $dt_mac {
    lassign $dt_mp dt_mx dt_my dt_mit
    set dt_best {}; set dt_bd 1e30
    foreach dt_i [$dt_blk getInsts] {
      if {[[ $dt_i getMaster] isBlock] || ![$dt_i isPlaced]} continue
      set dt_bb [$dt_i getBBox]
      set dt_x [expr {([$dt_bb xMin]+[$dt_bb xMax])/2}]
      set dt_y [expr {([$dt_bb yMin]+[$dt_bb yMax])/2}]
      set dt_d [expr {abs($dt_x-$dt_mx)+abs($dt_y-$dt_my)}]
      if {$dt_d < $dt_bd} { set dt_bd $dt_d; set dt_best [list $dt_x $dt_y $dt_mit] }
    }
    if {$dt_best eq ""} { error "OT_DTAP_MACRO_ONLY no legal standard-cell site for $dt_port" }
    lappend dt_macro_sinks $dt_best
  }
  set dt_ff $dt_macro_sinks; set dt_mac {}
}
# Planned anchors are an opt-in recipe input. The same local CTS, F4 co-location,
# macro-interface assignment and alignment below remain in use. Empty anchors are pruned;
# overloaded islands own multiple <=TARGET groups, rather than a remote unplanned tap.
proc dt_planned_groups {pts sites target} {
  array set members {}
  for {set k 0} {$k < [llength $sites]} {incr k} { set members($k) {} }
  foreach p $pts {
    set best 0; set bd 1e30; set k 0
    foreach xy $sites {
      lassign $xy x y
      set d [expr {abs([lindex $p 0]-$x)+abs([lindex $p 1]-$y)}]
      if {$d < $bd} { set bd $d; set best $k }
      incr k
    }
    lappend members($best) $p
  }
  set groups {}; set med {}
  for {set k 0} {$k < [llength $sites]} {incr k} {
    set S [lsort -integer -index 1 $members($k)]
    for {set j 0} {$j < [llength $S]} {incr j $target} {
      lappend groups [lrange $S $j [expr {$j+$target-1}]]
      lappend med [lindex $sites $k]
    }
  }
  return [list $groups $med]
}
# Optional reviewed short-chain groups: remove them before normal density
# partitioning, then append one real local-clock branch per complete group.
set dt_atomic_sets {}; set dt_atomic_med {}; set dt_atomic_pinned {}
set dt_native_sink_count [llength $dt_ff]
set ::ot_atomic_clock_pinned {}
if {[info exists ::env(OT_DTAP_ATOMIC_GROUPS)] && $::env(OT_DTAP_ATOMIC_GROUPS) ne ""} {
  if {[info exists ::env(OT_DTAP_SITES)] && $::env(OT_DTAP_SITES) ne ""} {error "ATOMIC_CLOCK cannot combine with planned density anchors"}
  source [file join [file dirname [info script]] core_clock_atomic_groups.tcl]
  set fh [open $::env(OT_DTAP_ATOMIC_GROUPS) r]; set groups [read $fh]; close $fh
  set points {}; foreach p $dt_ff {dict set points [[[lindex $p 2] getInst] getName] $p}
  set radius [expr {$::env(OT_DTAP_ATOMIC_RADIUS_UM) * $dt_u}]
  foreach record $groups {
    foreach name [lindex $record 1] {
      if {![dict exists $points $name]} continue
      set it [lindex [dict get $points $name] 2]
      if {![string match DFF* [[[$it getInst] getMaster] getName]] || [[$it getMTerm] getName] ni {CLK CK}} {
        error "ATOMIC_CLOCK member is not a native-root register clock pin: $name"
      }
    }
  }
  set plan [dt_atomic_plan $points $groups $::env(OT_DTAP_ATOMIC_MAX_SINKS) $radius]
  set dt_atomic_sets [dict get $plan sets]; set dt_atomic_med [dict get $plan med]
  set dt_atomic_pinned [dict get $plan pinned]; set dt_ff [dict get $plan rest]
  # The existing post-CTS F4 pass must not undo this explicit native-clock form.
  set ::ot_atomic_clock_pinned $dt_atomic_pinned
}
set dt_taps {}
set dt_of [dict create]
set dt_planned_active 0
if {[info exists ::env(OT_DTAP_SITES)] && $::env(OT_DTAP_SITES) ne ""} {
  set dt_planned_active 1
  set fh [open $::env(OT_DTAP_SITES) r]; set raw [read $fh]; close $fh
  set sites {}
  foreach xy [string trim $raw] {
    if {[llength $xy] != 2} { error "OT_DTAP_SITES needs {x y} records" }
    lassign $xy x y
    set x [expr {int(round($x*$dt_u))}]; set y [expr {int(round($y*$dt_u))}]
    foreach i [$dt_blk getInsts] {
      if {![[$i getMaster] isBlock]} continue
      set bb [$i getBBox]
      if {$x >= [$bb xMin] && $x <= [$bb xMax] && $y >= [$bb yMin] && $y <= [$bb yMax]} {
        error "planned clock anchor lies on macro [$i getName]"
      }
    }
    lappend sites [list $x $y]
  }
  if {![llength $sites]} { error "OT_DTAP_SITES empty" }
  lassign [dt_planned_groups $dt_ff $sites $dt_target] dt_sets dt_med
  puts "OT_DTAP_PLANNED anchors=[llength $sites] occupied_groups=[llength $dt_sets] sinks=[llength $dt_ff]"
} else {
set dt_sets [dt_split $dt_ff]
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
}
set dt_regular_count [llength $dt_sets]
set dt_sets [concat $dt_sets $dt_atomic_sets]
set dt_med [concat $dt_med $dt_atomic_med]
if {[llength $dt_atomic_sets]} {puts "OT_DTAP_ATOMIC groups [llength $dt_atomic_sets] pinned [dict size $dt_atomic_pinned]"}
# stray sinks (the robust split ignores the outer 2%): a sink farther than DMAX from its own tap joins the nearest tap
set dt_moved 0
# DIE-HEAD-86: the stray/planned-split pass reads the atomic pin set and the regular tap count; defaults when
# no atomic plan ran (the block is also sourced stand-alone by test_planned_group_caps)
if {![info exists dt_atomic_pinned]} {set dt_atomic_pinned {}}
if {![info exists dt_regular_count]} {set dt_regular_count [llength $dt_sets]}
array unset dt_asg
for {set k 0} {$k < [llength $dt_sets]} {incr k} { set dt_asg($k) {} }
set k 0
foreach S $dt_sets {
  lassign [lindex $dt_med $k] mx my
  foreach p $S {
    set t $k
    # Planned groups already use nearest anchors and explicit load splitting.
    # Reassigning distant members would collapse co-located split groups onto
    # their first anchor, defeating the planned sink cap (hfd:1942 vs1250).
    if {!$dt_planned_active && abs([lindex $p 0] - $mx) + abs([lindex $p 1] - $my) > $dt_dmax && !([dict size $dt_atomic_pinned] && [dict exists $dt_atomic_pinned [[[lindex $p 2] getInst] getName]])} {
      set bd 1e30
      for {set j 0} {$j < $dt_regular_count} {incr j} {
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
array unset dt_load
for {set k 0} {$k < [llength $dt_sets]} {incr k} {set dt_load($k) [llength $dt_asg($k)]}
proc dt_f4_group_move {mapping loads capture target cap planned} {
  upvar 1 $mapping groups $loads count
  set prior [dict get $groups $capture]
  if {$planned && $count($target) >= $cap} {return 0}
  dict set groups $capture $target
  incr count($prior) -1; incr count($target)
  return 1
}
dict for {nm p} $dt_pt {
  set t [dict get $dt_tp $nm]
  foreach o [[[lindex $p 2] getInst] getITerms] {
    if {![$o isOutputSignal]} continue
    set n [$o getNet]; if {$n eq "NULL" || $n eq ""} continue
    if {[$n getSigType] ne "SIGNAL"} continue
    foreach c [dt_d_sinks $n 1] {
      if {[dict exists $dt_atomic_pinned $nm] || [dict exists $dt_atomic_pinned $c]} continue
      if {![dict exists $dt_tp $c] || [dict get $dt_tp $c] == $t} continue
      set q [dict get $dt_pt $c]
      if {abs([lindex $q 0] - [lindex $p 0]) + abs([lindex $q 1] - [lindex $p 1]) > $dt_dmax / 2} continue
      if {[dt_f4_group_move dt_tp dt_load $c $t $dt_target $dt_planned_active]} {incr dt_f4}
    }
  }
}
array unset dt_asg
for {set k 0} {$k < [llength $dt_sets]} {incr k} { set dt_asg($k) {} }
dict for {nm p} $dt_pt { lappend dt_asg([dict get $dt_tp $nm]) $p }
dict for {name id} $dt_atomic_pinned {
  if {![dict exists $dt_tp $name]} {error "ATOMIC_CLOCK lost member $name"}
}
for {set k 0} {$k < [llength $dt_sets]} {incr k} {
  set S $dt_asg($k)
  if {![llength $S]} continue
  lassign [lindex $dt_med $k] mx my
  set inst [odb::dbInst_create $dt_blk $dt_master "ot_dtap_[expr {$dt_id_offset + $k}]"]
  $inst setLocation $mx $my
  $inst setPlacementStatus PLACED
  set net [odb::dbNet_create $dt_blk "ot_dtap_net_[expr {$dt_id_offset + $k}]"]
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
  set i [$dt_blk findInst "ot_dtap_[expr {$dt_id_offset + [lindex $t 0]}]"]; lassign [$i getLocation] lx ly
  lappend dt_lines [format "OT_DTAP tap %d sinks %d at %.2f %.2f um (medoid %.2f %.2f)" [expr {$dt_id_offset + [lindex $t 0]}] [lindex $t 4] [expr {$lx / double($dt_u)}] [expr {$ly / double($dt_u)}] [expr {[lindex $t 1] / double($dt_u)}] [expr {[lindex $t 2] / double($dt_u)}]]
}
foreach l $dt_lines { puts $l }
foreach l $dt_mrep { puts "OT_DTAP macro $l" }
puts "OT_DTAP done: $dt_moved stray sinks re-homed; $dt_f4 zero-logic capture regs joined their launch tap (F4); [llength $dt_taps] density taps for $dt_native_sink_count register sinks (target $dt_target/tap), [llength $dt_mac] macro clock pins on nearest tap"
if {[info exists ::env(OT_DTAP_OUT)]} { set fh [open $::env(OT_DTAP_OUT) [expr {[info exists ::env(OT_DTAP_APPEND)] && $::env(OT_DTAP_APPEND) ? "a" : "w"}]]; puts $fh [join [concat $dt_lines $dt_mrep] "\n"]; close $fh }
}
