# QC-NK-HOLD A+P (gen_phys core_input_place), PRE_DETAIL_PLACE at the end of face_flops_release.tcl: spread the zero-logic register chain
# that feeds each NK pipe register (u_pc_nk_*) evenly along a macro-avoiding Manhattan route from the chain head to
# the pipe register.  pilot7 measured the class: GPL (wirelength only) left all 10 stages of e.g. u_d10_u_t_3_2_n_y
# within 150 um of the head and paid 1350 um in the last hop (TT -1131 ps at u_pc D).  Same class as S81-RCK-4
# chain_even.tcl, but the route bends around the hard cores instead of a straight line through them.
# No netlist change; stages and their hop buffers only move (PLACED), DPL legalizes.
uplevel #0 {
set nc_blk [ord::get_db_block]
set nc_dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set nc_core [$nc_blk getCoreArea]
set nc_halo [expr {round(9.0 * $nc_dbu)}]
set nc_mac {}
foreach i [$nc_blk getInsts] { if {[[$i getMaster] isBlock]} { set b [$i getBBox]; lappend nc_mac [list [$b xMin] [$b yMin] [$b xMax] [$b yMax]] } }
# street centre lines: core edges, gaps between macros (both axes)
proc nc_lines {lo hi ivals} {
  set iv [lsort -integer -index 0 $ivals]; set out {}; set cur $lo
  foreach v $iv { lassign $v a b; if {$a > $cur} { lappend out [expr {($cur + $a) / 2}] }; if {$b > $cur} { set cur $b } }
  if {$hi > $cur} { lappend out [expr {($cur + $hi) / 2}] }
  return $out
}
set nc_xi {}; set nc_yi {}
foreach m $nc_mac { lassign $m a b c d; lappend nc_xi [list $a $c]; lappend nc_yi [list $b $d] }
set nc_xs [nc_lines [$nc_core xMin] [$nc_core xMax] $nc_xi]
set nc_ys [nc_lines [$nc_core yMin] [$nc_core yMax] $nc_yi]
proc nc_hit {x1 y1 x2 y2} {
  global nc_mac
  set e 2000
  foreach m $nc_mac {
    lassign $m a b c d
    if {$y1 == $y2} { if {$y1 > $b+$e && $y1 < $d-$e && max($x1,$x2) > $a+$e && min($x1,$x2) < $c-$e} { return 1 } } \
    else { if {$x1 > $a+$e && $x1 < $c-$e && max($y1,$y2) > $b+$e && min($y1,$y2) < $d-$e} { return 1 } }
  }
  return 0
}
proc nc_len {pts} { set l 0; for {set k 1} {$k < [llength $pts]} {incr k} { lassign [lindex $pts [expr {$k-1}]] a b; lassign [lindex $pts $k] c d; set l [expr {$l + abs($c-$a) + abs($d-$b)}] }; return $l }
proc nc_ok {pts} { for {set k 1} {$k < [llength $pts]} {incr k} { lassign [lindex $pts [expr {$k-1}]] a b; lassign [lindex $pts $k] c d; if {[nc_hit $a $b $c $d]} { return 0 } }; return 1 }
# shortest Manhattan route with up to 2 bends (HVH / VHV) or 4 bends (HVHVH via two street lines) that clears macros
proc nc_route {hx hy tx ty} {
  global nc_xs nc_ys
  set best {}; set bl 0
  set cands {}
  foreach x [concat $hx $tx $nc_xs] { lappend cands [list [list $hx $hy] [list $x $hy] [list $x $ty] [list $tx $ty]] }
  foreach y [concat $hy $ty $nc_ys] { lappend cands [list [list $hx $hy] [list $hx $y] [list $tx $y] [list $tx $ty]] }
  foreach x $nc_xs { foreach y $nc_ys {
    lappend cands [list [list $hx $hy] [list $x $hy] [list $x $y] [list $tx $y] [list $tx $ty]]
    lappend cands [list [list $hx $hy] [list $hx $y] [list $x $y] [list $x $ty] [list $tx $ty]]
  } }
  foreach x1 $nc_xs { foreach y $nc_ys { foreach x2 $nc_xs {
    lappend cands [list [list $hx $hy] [list $x1 $hy] [list $x1 $y] [list $x2 $y] [list $x2 $ty] [list $tx $ty]]
  } } }
  foreach y1 $nc_ys { foreach x $nc_xs { foreach y2 $nc_ys {
    lappend cands [list [list $hx $hy] [list $hx $y1] [list $x $y1] [list $x $y2] [list $tx $y2] [list $tx $ty]]
  } } }
  foreach p $cands { if {![nc_ok $p]} continue; set l [nc_len $p]; if {$best eq {} || $l < $bl} { set best $p; set bl $l } }
  if {$best eq {}} { set best [list [list $hx $hy] [list $tx $ty]] }
  return $best
}
proc nc_at {pts f} {
  set L [nc_len $pts]; set want [expr {$f * $L}]; set acc 0
  for {set k 1} {$k < [llength $pts]} {incr k} {
    lassign [lindex $pts [expr {$k-1}]] a b; lassign [lindex $pts $k] c d
    set s [expr {abs($c-$a) + abs($d-$b)}]
    if {$acc + $s >= $want && $s > 0} { set t [expr {double($want-$acc)/$s}]; return [list [expr {$a+($c-$a)*$t}] [expr {$b+($d-$b)*$t}]] }
    set acc [expr {$acc + $s}]
  }
  return [lindex $pts end]
}
proc nc_put {inst x y} {
  global nc_mac nc_halo nc_core
  set w [[$inst getMaster] getWidth]; set h [[$inst getMaster] getHeight]
  foreach m $nc_mac {
    lassign $m a b c d; set a [expr {$a-$nc_halo}]; set b [expr {$b-$nc_halo}]; set c [expr {$c+$nc_halo}]; set d [expr {$d+$nc_halo}]
    if {$x > $a && $x < $c && $y > $b && $y < $d} {
      lassign [lindex [lsort -real -index 0 [list [list [expr {$x-$a}] $a $y] [list [expr {$c-$x}] $c $y] [list [expr {$y-$b}] $x $b] [list [expr {$d-$y}] $x $d]]] 0] _ x y
    }
  }
  set x [expr {max([$nc_core xMin], min([$nc_core xMax]-$w, $x))}]
  set y [expr {max([$nc_core yMin], min([$nc_core yMax]-$h, $y))}]
  $inst setLocation [expr {int($x)}] [expr {int($y)}]
  if {[$inst getPlacementStatus] in {UNPLACED FIRM}} { $inst setPlacementStatus PLACED }
}
proc nc_isbuf {inst} { set m [[$inst getMaster] getName]; return [expr {[string match "BUF*" $m] || [string match "INV*" $m] || [string match "HB*" $m]}] }
# face-anchored registers (face_flops.tcl pin registers, released just before this hook) stay where they are: they
# end a chain like a fixed head
set nc_face {}
if {[info exists ::env(RESULTS_DIR)] && [file exists $::env(RESULTS_DIR)/ot_face_flops.txt]} {
  set f [open $::env(RESULTS_DIR)/ot_face_flops.txt]; foreach l [split [read $f] "\n"] { set l [string trim $l]; if {$l ne ""} { dict set nc_face $l 1 } }; close $f
}
proc nc_mov {inst} { global nc_face; return [expr {[$inst getPlacementStatus] ni {FIRM LOCKED COVER} && ![dict exists $nc_face [$inst getName]]}] }
# driver of an input iterm through buffers: {driver_iterm {buffers nearest-first}}
proc nc_back {it} {
  set bufs {}; set net [$it getNet]
  for {set k 0} {$k < 40} {incr k} {
    if {$net eq "NULL" || $net eq ""} { return [list "" $bufs] }
    set drv ""
    foreach t [$net getITerms] { if {[$t isOutputSignal]} { set drv $t } }
    if {$drv eq ""} { return [list "" $bufs] }
    set di [$drv getInst]
    if {[[$di getMaster] isBlock] || ![nc_isbuf $di]} { return [list $drv $bufs] }
    lappend bufs $di
    set net ""; foreach t [$di getITerms] { if {[$t isInputSignal] && [$t getNet] ne "NULL" && [[$t getNet] getSigType] eq "SIGNAL"} { set net [$t getNet] } }
  }
  return [list "" $bufs]
}
proc nc_loads {inst} {
  set n 0
  foreach t [$inst getITerms] { if {[$t isOutputSignal] && [$t getNet] ne "NULL"} {
    set front [list [$t getNet]]
    for {set d 0} {$d < 40 && [llength $front]} {incr d} { set nf {}
      foreach net $front { foreach x [$net getITerms] { if {![$x isInputSignal]} continue; set xi [$x getInst]
        if {![[$xi getMaster] isBlock] && [nc_isbuf $xi]} { foreach o [$xi getITerms] { if {[$o isOutputSignal] && [$o getNet] ne "NULL"} { lappend nf [$o getNet] } } } else { incr n } } }
      set front $nf }
  } }
  return $n
}
proc nc_dpin {inst} { foreach t [$inst getITerms] { if {[[$t getMTerm] getName] eq "D"} { return $t } }; return "" }
proc nc_ctr {o} { set b [$o getBBox]; return [list [expr {([$b xMin]+[$b xMax])/2}] [expr {([$b yMin]+[$b yMax])/2}]] }
set nc_chains 0; set nc_moved 0; set nc_l0 {}; set nc_l1 {}; set nc_rc {}
foreach pc [$nc_blk getInsts] {
  if {![regexp {u_pc_nk_} [$pc getName]] || ![string match "DFF*" [[$pc getMaster] getName]]} continue
  # backward: hops {stage_inst bufs_on_its_D}, stages = movable fanout-1 zero-logic chain registers
  set seq {}; set hopb {}; set cur $pc; set head ""
  while {[llength $seq] < 24} {
    set dp [nc_dpin $cur]; if {$dp eq ""} break
    lassign [nc_back $dp] drv bufs
    lappend hopb $bufs
    if {$drv eq ""} break
    set di [$drv getInst]
    set nm [string map {\\ {}} [$di getName]]
    if {![[$di getMaster] isBlock] && [string match "DFF*" [[$di getMaster] getName]] && [nc_mov $di] \
        && [regexp {(u_d[0-9]+_|u_lpad_|u_r8b_strap_|u_pd[0-9]+_)} $nm] && ![regexp {u_pc_nk_} $nm] && [nc_loads $di] == 1} {
      set seq [linsert $seq 0 $di]; set cur $di; continue
    }
    set head $drv; break
  }
  if {$head eq "" || ![llength $seq]} continue
  # head: driver flop/pin position; tail: the pipe register (anchored at the NK pin)
  if {[[[$head getInst] getMaster] isBlock]} { lassign [nc_ctr $head] hx hy } else { lassign [nc_ctr [$head getInst]] hx hy }
  lassign [nc_ctr $pc] tx ty
  set route [nc_route $hx $hy $tx $ty]
  set hops [expr {[llength $seq] + 1}]
  # before: longest single hop (Manhattan) along head -> stages -> pc
  set prev [list $hx $hy]; set mx 0
  foreach s [concat $seq [list $pc]] { lassign [nc_ctr $s] x y; set mx [expr {max($mx, abs($x-[lindex $prev 0])+abs($y-[lindex $prev 1]))}]; set prev [list $x $y] }
  lappend nc_l0 [expr {$mx/double($nc_dbu)}]
  lappend nc_l1 [expr {[nc_len $route]/double($hops)/$nc_dbu}]
  dict incr nc_rc [expr {[llength $route]-2}]
  for {set j 0} {$j < [llength $seq]} {incr j} {
    lassign [nc_at $route [expr {double($j+1)/$hops}]] x y
    nc_put [lindex $seq $j] $x $y; incr nc_moved
  }
  # buffers: hopb[k] are the buffers on the D of (pc, seq[end], seq[end-1], ...) nearest-first
  set n [llength $seq]
  # (the head hop's buffers may be shared with other loads of the head: left where GPL put them)
  for {set k 0} {$k < min([llength $hopb], $n)} {incr k} {
    set bs [lindex $hopb $k]; set nb [llength $bs]; if {!$nb} continue
    set hopi [expr {$n - $k}]   ;# hop index: from position hopi to hopi+1 (sink side)
    for {set q 0} {$q < $nb} {incr q} {
      set bi [lindex $bs $q]; if {![nc_mov $bi]} continue
      set f [expr {($hopi + 1 - double($q+1)/($nb+1)) / $hops}]
      if {$f < 0} { set f 0 }
      lassign [nc_at $route $f] x y; nc_put $bi $x $y
    }
  }
  incr nc_chains
}
proc nc_pct {l p} { if {![llength $l]} { return na }; set l [lsort -real $l]; return [format %.0f [lindex $l [expr {min([llength $l]-1, int([llength $l]*$p))}]]] }
puts "OT_NK_CHAIN chains $nc_chains stages_moved $nc_moved bends $nc_rc max_hop_um before p50 [nc_pct $nc_l0 0.5] p90 [nc_pct $nc_l0 0.9] max [nc_pct $nc_l0 1.0] after p50 [nc_pct $nc_l1 0.5] p90 [nc_pct $nc_l1 0.9] max [nc_pct $nc_l1 1.0]"
}
