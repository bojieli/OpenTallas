# QC-P5 10-23 A0 v4 (COORD A0-clock concern; R4 revised): local clock trees under the core's tap pins.
# The A0 core has 8 clock ports (ck + ck_t1..ck_t7, OT_A0_CK_TAPS): 2 columns (W/E faces) x 4 rows of ~229 x 289 um
# regions.  All carry the same die clock from the CB quad's tap grid (equal arrival, neighbour <= 80 ps).  The RTL
# clocks every flop/macro from ck; here (PRE_CTS) every sink moves to its NEAREST tap port (die_plan clock_taps.tcl,
# PLAN-TOOL2 claude/plan-tool-1023 @4992d4f30, port names ck/ck_t<i>), taps over OT_TAP_MAX_SINKS split into slabs,
# and after clock_tree_synthesis the tap trees are balanced to 250 +/- 40 ps (die_plan tap_balance.tcl, same tip).
# Replaces the v1-v3 single ck pin + 48 k-means roots under one TritonCTS top tree (NK v2 1,133 ps: 17-level top tree
# 558 ps + 313 ps balance pads; probe QC-P5 10-23).
# The type has one clock port per die-spine tap (clk, clk_t1, ...; pitch <= 600 um, schema.tap_grid).  The RTL
# clocks every flop from 'clk'; here every sink on the clk net moves to the net of its NEAREST tap port, so CTS builds
# one local tree per tap (radius <= ~300 um) instead of one tree from one interior tap (CP1: 1176 ps, 29-32 levels).
set ct_blk [ord::get_db_block]
set ct_taps {}
foreach bt [$ct_blk getBTerms] {
  set n [$bt getName]
  if {![regexp {^ck(_t[0-9]+)?$} $n]} continue
  set bb [$bt getBBox]
  set net [$bt getNet]
  if {$net eq "NULL" || $net eq ""} {
    set net [odb::dbNet_create $ct_blk "${n}_net"]
    $bt connect $net
  }
  $net setSigType CLOCK
  lappend ct_taps [list $n $net [expr {([$bb xMin] + [$bb xMax]) / 2}] [expr {([$bb yMin] + [$bb yMax]) / 2}]]
}
if {[llength $ct_taps] < 2} {
  puts "OT_CLOCK_TAPS single tap: nothing to split"
} else {
  set root [[$ct_blk findBTerm ck] getNet]
  set cnt {}
  set moved 0
  foreach it [$root getITerms] {
    if {[[$it getMTerm] getIoType] ne "INPUT"} continue
    set i [$it getInst]
    set loc [$i getLocation]
    set x [lindex $loc 0]; set y [lindex $loc 1]
    set best ""; set bd 0
    foreach tp $ct_taps {
      set d [expr {abs($x - [lindex $tp 2]) + abs($y - [lindex $tp 3])}]
      if {$best eq "" || $d < $bd} { set best $tp; set bd $d }
    }
    dict incr cnt [lindex $best 0]
    if {[lindex $best 1] ne $root} {
      $it disconnect
      $it connect [lindex $best 1]
      incr moved
    }
  }
  puts "OT_CLOCK_TAPS [llength $ct_taps] taps, $moved sinks moved off clk: [lsort -stride 2 -index 0 $cnt]"
}
# COORD 10-23: size taps by SINK COUNT.  A tap whose nearest-sink set exceeds OT_TAP_MAX_SINKS (~3k) is split into
# k = ceil(n / cap) equal-count slabs along the wider axis of its sinks; each slab hangs off its own net behind one
# split buffer placed at the slab centroid, so CTS builds k smaller trees (CP1 r6: 3.6-4.8k-sink taps 300-313 ps).
set ct_cap [expr {[info exists ::env(OT_TAP_MAX_SINKS)] ? $::env(OT_TAP_MAX_SINKS) : 3000}]
set ct_bufm [[ord::get_db] findMaster [expr {[info exists ::env(OT_TAP_SPLIT_BUF)] ? $::env(OT_TAP_SPLIT_BUF) : "BUFx24_ASAP7_75t_R"}]]
set ct_split {}
foreach tp $ct_taps {
  set n [lindex $tp 0]; set net [lindex $tp 1]
  set sinks {}
  foreach it [$net getITerms] {
    if {[[$it getMTerm] getIoType] ne "INPUT"} continue
    set loc [[$it getInst] getLocation]
    lappend sinks [list $it [lindex $loc 0] [lindex $loc 1]]
  }
  set ns [llength $sinks]
  set k [expr {int(ceil($ns / double($ct_cap)))}]
  if {$k < 2} continue
  set xs [lmap e $sinks {lindex $e 1}]; set ys [lmap e $sinks {lindex $e 2}]
  set ax [expr {([tcl::mathfunc::max {*}$xs] - [tcl::mathfunc::min {*}$xs]) >= ([tcl::mathfunc::max {*}$ys] - [tcl::mathfunc::min {*}$ys]) ? 1 : 2}]
  set sinks [lsort -integer -index $ax $sinks]
  set per [expr {int(ceil($ns / double($k)))}]
  for {set s 0} {$s < $k} {incr s} {
    set chunk [lrange $sinks [expr {$s * $per}] [expr {min($ns, ($s + 1) * $per) - 1}]]
    if {![llength $chunk]} continue
    set sx 0; set sy 0
    foreach e $chunk { set sx [expr {$sx + [lindex $e 1]}]; set sy [expr {$sy + [lindex $e 2]}] }
    set cx [expr {int($sx / [llength $chunk])}]; set cy [expr {int($sy / [llength $chunk])}]
    set snet [odb::dbNet_create $ct_blk "${n}_split$s"]
    $snet setSigType CLOCK
    set b [odb::dbInst_create $ct_blk $ct_bufm "${n}_splitbuf$s"]
    foreach t [$b getITerms] {
      set mt [$t getMTerm]
      if {[$mt getSigType] in {POWER GROUND}} continue
      if {[$mt getIoType] eq "INPUT"} { $t connect $net } elseif {[$mt getIoType] eq "OUTPUT"} { $t connect $snet }
    }
    $b setLocation $cx $cy
    $b setPlacementStatus PLACED
    foreach e $chunk { set it [lindex $e 0]; $it disconnect; $it connect $snet }
  }
  lappend ct_split "$n:$ns->${k}x$per"
}
if {[llength $ct_split]} {
  detailed_placement
  puts "OT_CLOCK_TAPS split dense taps (cap $ct_cap sinks): $ct_split"
} else {
  puts "OT_CLOCK_TAPS no tap over $ct_cap sinks"
}
# ---- post-CTS tap balance (die_plan tap_balance.tcl body, ck ports, clock core_clk), run right after CTS
set ::ot_a0_tb_src {
uplevel #0 {
set tb_blk [ord::get_db_block]
set tb_dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set tb_target [expr {[info exists ::env(OT_TAP_TARGET_PS)] ? $::env(OT_TAP_TARGET_PS) : 250.0}]
set tb_win [expr {[info exists ::env(OT_TAP_WINDOW_PS)] ? $::env(OT_TAP_WINDOW_PS) : 40.0}]
set tb_tol [expr {[info exists ::env(OT_TAP_TOL_PS)] ? $::env(OT_TAP_TOL_PS) : 15.0}]
set tb_ronly [expr {[info exists ::env(OT_TAP_REPORT_ONLY)] && $::env(OT_TAP_REPORT_ONLY)}]
set tb_pitch [expr {[info exists ::env(OT_TAP_PITCH_UM)] ? $::env(OT_TAP_PITCH_UM) : 600.0}]
set tb_cell [expr {[info exists ::env(OT_TAP_DELAY_CELL)] ? $::env(OT_TAP_DELAY_CELL) : "BUFx4_ASAP7_75t_R"}]
set tb_master [[ord::get_db] findMaster $tb_cell]
proc tb_is_buf {inst} {
  set m [[$inst getMaster] getName]
  return [expr {[string match "BUF*" $m] || [string match "INV*" $m] || [string match "CKINV*" $m] || [string match "HB*" $m]}]
}
proc tb_sinks {net} {
  set out {}; set todo [list $net]; set seen {}
  while {[llength $todo]} {
    set n [lindex $todo end]; set todo [lrange $todo 0 end-1]
    if {[dict exists $seen [$n getName]]} continue
    dict set seen [$n getName] 1
    foreach it [$n getITerms] {
      if {[[$it getMTerm] getIoType] ne "INPUT"} continue
      set i [$it getInst]
      if {[tb_is_buf $i]} {
        foreach o [$i getITerms] { if {[[$o getMTerm] getIoType] eq "OUTPUT" && [$o getNet] ne "NULL"} { lappend todo [$o getNet] } }
      } else { lappend out "[$i getName]/[[$it getMTerm] getName]" }
    }
  }
  return $out
}
proc tb_rise {pin half} {
  # rise-edge insertion: OpenSTA's max over clock edges can return the falling edge (+T/2)
  set a [get_property $pin arrival_max_rise]
  if {$a eq "" || $a eq "INF" || $a eq "-INF"} { return "" }
  if {$a >= $half} { set a [expr {$a - $half}] }
  return $a
}
proc tb_measure {{est 1}} {
  global tb_blk
  if {$est} { estimate_parasitics -placement }
  set_propagated_clock [all_clocks]
  set half [expr {[get_property [get_clocks core_clk] period] / 2.0}]
  set res {}
  foreach bt [$tb_blk getBTerms] {
    set n [$bt getName]
    if {![regexp {^ck(_t[0-9]+)?$} $n]} continue
    set net [$bt getNet]
    if {$net eq "NULL"} continue
    set s 0.0; set k 0; set mx 0.0; set mn 1e9
    foreach p [tb_sinks $net] {
      set pin [get_pins -quiet $p]
      if {$pin eq ""} continue
      set a [tb_rise $pin $half]
      if {$a eq ""} continue
      set s [expr {$s + $a}]; incr k
      set mx [expr {max($mx, $a)}]; set mn [expr {min($mn, $a)}]
    }
    if {$k} { dict set res $n [list [expr {$s / $k}] $mn $mx $k $bt] }
  }
  return $res
}
proc tb_line {tag m} {
  set line $tag
  dict for {n v} $m { append line " $n=[format %.0f [lindex $v 0]]([format %.0f [lindex $v 1]]-[format %.0f [lindex $v 2]],[lindex $v 3])" }
  return $line
}
set tb_added 0
if {$tb_ronly} {
  set m [tb_measure 0]
  set lo 1e9; set hi 0.0; set mx 0.0
  dict for {n v} $m { set lo [expr {min($lo, [lindex $v 1])}]; set hi [expr {max($hi, [lindex $v 2])}] }
  puts "[tb_line {OT_TAP_RC mean(min-max,sinks):} $m]"
  puts "OT_TAP_RC sink insertion [format %.0f $lo]..[format %.0f $hi] ps (partition skew [format %.0f [expr {$hi - $lo}]]; limit [format %.0f [expr {$tb_target + $tb_win}]])"
} else {
for {set it 0} {$it < 4} {incr it} {
  set m [tb_measure]
  set longest 0.0
  dict for {n v} $m { set longest [expr {max($longest, [lindex $v 0])}] }
  # target fixed at the first pass (padding overshoot must not ratchet it up); a padded tree's slowest sink stays
  # <= ins + tol
  if {$it == 0} { set tgt [expr {min($tb_target + $tb_win, max($tb_target - $tb_win, $longest))}] }
  puts "[tb_line "OT_TAP_BALANCE it$it target [format %.0f $tgt]:" $m]"
  set todo 0
  dict for {n v} $m {
    set d [expr {min($tgt - [lindex $v 0], $tb_target + $tb_win - [lindex $v 2])}]
    if {$d <= $tb_tol} continue
    set todo 1
    # ~18 ps per BUFx4 stage on a short local net; insert 3/4 of the estimate per pass and re-measure
    set nb [expr {max(1, int(round($d / 18.0 * 0.75)))}]
    set bt [lindex $v 4]
    set root [$bt getNet]
    set bb [$bt getBBox]
    set x [expr {([$bb xMin] + [$bb xMax]) / 2}]; set y [expr {([$bb yMin] + [$bb yMax]) / 2}]
    # the tree hangs off a new net; the chain runs tap port -> buf ... -> new net
    set tree [odb::dbNet_create $tb_blk "${n}_tb${it}_tree"]
    $tree setSigType CLOCK
    foreach t [$root getITerms] { $t disconnect; $t connect $tree }
    set prev $root
    for {set b 0} {$b < $nb} {incr b} {
      set inst [odb::dbInst_create $tb_blk $tb_master "${n}_tb${it}_d$b"]
      set nxt [expr {$b == $nb - 1 ? $tree : [odb::dbNet_create $tb_blk "${n}_tb${it}_n$b"]}]
      if {$nxt ne $tree} { $nxt setSigType CLOCK }
      foreach t [$inst getITerms] {
        set mt [$t getMTerm]
        if {[$mt getSigType] in {POWER GROUND}} continue
        if {[$mt getIoType] eq "INPUT"} { $t connect $prev } elseif {[$mt getIoType] eq "OUTPUT"} { $t connect $nxt }
      }
      $inst setLocation [expr {$x + $b * 2 * [$tb_master getWidth]}] $y
      $inst setPlacementStatus PLACED
      set prev $nxt
      incr tb_added
    }
  }
  if {!$todo} break
  detailed_placement
}
set m [tb_measure]
set lo 1e9; set hi 0.0; set fail {}
dict for {n v} $m {
  set lo [expr {min($lo, [lindex $v 0])}]; set hi [expr {max($hi, [lindex $v 0])}]
  if {[lindex $v 2] > $tb_target + $tb_win} { lappend fail "$n=[format %.0f [lindex $v 2]]" }
}
puts "OT_TAP_BALANCE done: $tb_added delay cells; tap mean insertion [format %.0f $lo]..[format %.0f $hi] ps (spread [format %.0f [expr {$hi - $lo}]])"
if {[llength $fail]} {
  # insertion ~ grows with the tree span; shrink the pitch by the overshoot ratio
  set sug [expr {$tb_pitch * ($tb_target + $tb_win) / max($hi, 1.0)}]
  puts "OT_TAP_CHECK FAIL trees over [format %.0f [expr {$tb_target + $tb_win}]] ps: $fail; re-pitch taps to <= [format %.0f $sug] um (partition clock.tap_pitch_um)"
} else {
  puts "OT_TAP_CHECK OK every tap tree <= [format %.0f [expr {$tb_target + $tb_win}]] ps"
}
}
}
}
rename clock_tree_synthesis ::ot_a0_cts_orig
proc clock_tree_synthesis {args} {
  ::ot_a0_cts_orig {*}$args
  eval $::ot_a0_tb_src
}
