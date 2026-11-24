# QC-NK-HOLD A+P (gen_phys core_input_place), PRE_RESIZE (after GPL, before repair_design buffers the new hops): spread the zero-logic register chain
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
# CB-CHAIN-LANE (QC-CB-SPREAD-R2 11-24, COORD 10:1x): nc_route bends every chain onto the street CENTRE line, so all 514
# bits of a bus (pipe stages, r8b strap pads, pd pads and their hop buffers) stacked in one gcell column (cbn_q00 west
# street x~52: pq_/lk_/lpad nets 2-2.5k GRT overflow each).  Each bit now takes its own lane across the street width:
# lane = lo + m + (hi - lo - 2m) * (b + 0.5) / n (b = the bit index of the chain tail, n = its bus width, m = halo + 2 um),
# applied to every route leg >= 20 um that runs along a street (centre line or the tail / head column; a moved first or
# last leg gets a jog, head / tail stay), kept only when the laned route still clears every macro (nc_ok), else the old route.  OT_NK_CHAIN_LANE=0 restores the centre line.
proc nc_gaps {lo hi ivals} {
  set iv [lsort -integer -index 0 $ivals]; set out {}; set cur $lo
  foreach v $iv { lassign $v a b; if {$a > $cur} { lappend out [list [expr {($cur + $a) / 2}] $cur $a] }; if {$b > $cur} { set cur $b } }
  if {$hi > $cur} { lappend out [list [expr {($cur + $hi) / 2}] $cur $hi] }
  return $out
}
proc nc_lane_pos {lo hi b n margin} {
  set w [expr {$hi - $lo - 2 * $margin}]
  if {$n < 2 || $w <= 0} { return [expr {($lo + $hi) / 2}] }
  return [expr {int(round($lo + $margin + $w * ($b + 0.5) / double($n)))}]
}
# the street (lo hi) of the gap list {{mid lo hi} ...} that holds coordinate v, {} when v is not in a street
proc nc_gap_of {gaps v} { foreach g $gaps { lassign $g m a c; if {$v >= $a && $v <= $c} { return [list $a $c] } }; return {} }
# every route leg at least lmin long that runs ALONG a street (a vertical leg inside an x street, a horizontal leg inside a
# y street) moves to the bit's lane of that street; a moved first / last leg gets a jog from the head / to the tail
proc nc_route_lane {pts xgaps ygaps b n margin lmin} {
  set N [expr {[llength $pts] - 1}]
  if {$n < 2 || $N < 1} { return $pts }
  set X {}; set Y {}; foreach p $pts { lappend X [lindex $p 0]; lappend Y [lindex $p 1] }
  set hj {}; set tj {}
  for {set i 0} {$i < $N} {incr i} {
    set x0 [lindex $X $i]; set y0 [lindex $Y $i]; set x1 [lindex $X [expr {$i+1}]]; set y1 [lindex $Y [expr {$i+1}]]
    if {$x0 == $x1 && abs($y1 - $y0) >= $lmin} {
      set g [nc_gap_of $xgaps $x0]; if {![llength $g]} continue
      set L [nc_lane_pos {*}$g $b $n $margin]
      if {$i > 0} { lset X $i $L } else { set hj [list $L $y0] }
      if {$i + 1 < $N} { lset X [expr {$i+1}] $L } else { set tj [list $L $y1] }
    } elseif {$y0 == $y1 && abs($x1 - $x0) >= $lmin} {
      set g [nc_gap_of $ygaps $y0]; if {![llength $g]} continue
      set L [nc_lane_pos {*}$g $b $n $margin]
      if {$i > 0} { lset Y $i $L } else { set hj [list $x0 $L] }
      if {$i + 1 < $N} { lset Y [expr {$i+1}] $L } else { set tj [list $x1 $L] }
    }
  }
  # a 2-point leg moved at both ends: head -> (L, hy) -> (L, ty) -> tail
  if {$N == 1 && [llength $hj] && [llength $tj]} { return [list [lindex $pts 0] $hj $tj [lindex $pts end]] }
  set out [list [lindex $pts 0]]
  if {[llength $hj]} { lappend out $hj }
  for {set k 1} {$k < $N} {incr k} { lappend out [list [lindex $X $k] [lindex $Y $k]] }
  if {[llength $tj]} { lappend out $tj }
  lappend out [lindex $pts end]
  return $out
}
# bus key of a register name: the name without its LAST [bit] index -> {key bit}, {} when it has none
proc nc_lane_key {nm} {
  set nm [string map {\\ {}} $nm]
  if {[regexp {^(.*)\[([0-9]+)\]([^\[\]]*)$} $nm -> pre bit post]} { return [list "$pre\[\]$post" $bit] }
  return {}
}
set nc_xgap [nc_gaps [$nc_core xMin] [$nc_core xMax] $nc_xi]
set nc_ygap [nc_gaps [$nc_core yMin] [$nc_core yMax] $nc_yi]
set nc_lane_on [expr {![info exists ::env(OT_NK_CHAIN_LANE)] || $::env(OT_NK_CHAIN_LANE) ne "0"}]
set nc_lane_m [expr {$nc_halo + round(2.0 * $nc_dbu)}]; set nc_lane_lmin [expr {round(20.0 * $nc_dbu)}]
set nc_lane_w {}; set nc_lane_used 0; set nc_lane_fallback 0
if {$nc_lane_on} {
  foreach i [$nc_blk getInsts] {
    set nm [$i getName]
    if {![regexp {u_pc_nk_|u_r8b_strap_} $nm]} continue
    set kb [nc_lane_key $nm]; if {![llength $kb]} continue
    lassign $kb key bit
    if {![dict exists $nc_lane_w $key] || [dict get $nc_lane_w $key] <= $bit} { dict set nc_lane_w $key [expr {$bit + 1}] }
  }
}
# the route of one bit's chain: the centre route, laned across its street(s) when the tail register names a bit of a bus
proc nc_route_bit {hx hy tx ty nm} {
  global nc_lane_on nc_lane_w nc_xgap nc_ygap nc_lane_m nc_lane_lmin nc_lane_used nc_lane_fallback
  set r [nc_route $hx $hy $tx $ty]
  if {!$nc_lane_on} { return $r }
  set kb [nc_lane_key $nm]; if {![llength $kb]} { return $r }
  lassign $kb key bit
  if {![dict exists $nc_lane_w $key]} { return $r }
  set r2 [nc_route_lane $r $nc_xgap $nc_ygap $bit [dict get $nc_lane_w $key] $nc_lane_m $nc_lane_lmin]
  if {$r2 eq $r} { return $r }
  if {![nc_ok $r2]} { incr nc_lane_fallback; return $r }
  incr nc_lane_used
  return $r2
}
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
proc nc_load_insts {inst} {
  set n {}
  foreach t [$inst getITerms] { if {[$t isOutputSignal] && [$t getNet] ne "NULL"} {
    set front [list [$t getNet]]
    for {set d 0} {$d < 40 && [llength $front]} {incr d} { set nf {}
      foreach net $front { foreach x [$net getITerms] { if {![$x isInputSignal]} continue; set xi [$x getInst]
        if {![[$xi getMaster] isBlock] && [nc_isbuf $xi]} { foreach o [$xi getITerms] { if {[$o isOutputSignal] && [$o getNet] ne "NULL"} { lappend nf [$o getNet] } } } else { lappend n $xi } } }
      set front $nf }
  } }
  return $n
}
proc nc_loads {inst} { return [llength [nc_load_insts $inst]] }
# FLOW-QC-N 11-17 (FABLE-FIX-QC-N, cbn_q01 n1b): the same walk, returning the terminal load ITERMS (the pin matters: a register
# reached at RESETN / SETN / CLK is not a data load of the xstn)
proc nc_load_terms {inst} {
  set n {}
  foreach t [$inst getITerms] { if {[$t isOutputSignal] && [$t getNet] ne "NULL"} {
    set front [list [$t getNet]]
    for {set d 0} {$d < 40 && [llength $front]} {incr d} { set nf {}
      foreach net $front { foreach x [$net getITerms] { if {![$x isInputSignal]} continue; set xi [$x getInst]
        if {![[$xi getMaster] isBlock] && [nc_isbuf $xi]} { foreach o [$xi getITerms] { if {[$o isOutputSignal] && [$o getNet] ne "NULL"} { lappend nf [$o getNet] } } } else { lappend n $x } } }
      set front $nf }
  } }
  return $n
}
# data pin of a register (pure): the clock and the asynchronous reset / set pins are not data
proc nc_data_pin {pin} { return [expr {$pin ni {CLK RESETN SETN}}] }
# coordinate-wise median of points {{x y} ...} (pure): the place of a buffer between its driver and its loads that adds no
# detour to any of them when there are three, and the least total wire otherwise; two points give their midpoint
proc nc_median_pt {pts} {
  set n [llength $pts]; if {!$n} { return {} }
  set out {}
  foreach k {0 1} {
    set v {}; foreach p $pts { lappend v [lindex $p $k] }
    set v [lsort -real $v]
    if {$n % 2} { lappend out [lindex $v [expr {$n/2}]] } else { lappend out [expr {([lindex $v [expr {$n/2-1}]] + [lindex $v [expr {$n/2}]]) / 2.0}] }
  }
  return $out
}
# a point clamped into the box x0 y0 x1 y1 (pure)
proc nc_clamp_box {x y x0 y0 x1 y1} { return [list [expr {max($x0, min($x1, $x))}] [expr {max($y0, min($y1, $y))}]] }
# centres of the direct driver and the direct loads of a buffer/inverter (blocks excluded)
proc nc_buf_neigh {inst} {
  set pts {}
  foreach t [$inst getITerms] {
    set net [$t getNet]; if {$net eq "NULL" || $net eq "" || [$net getSigType] ne "SIGNAL"} continue
    foreach x [$net getITerms] {
      if {[$t isInputSignal] ? ![$x isOutputSignal] : !([$t isOutputSignal] && [$x isInputSignal])} continue
      set xi [$x getInst]; if {$xi eq $inst || [[$xi getMaster] isBlock]} continue
      lappend pts [nc_ctr $xi]
    }
  }
  return $pts
}
# every non-buffer load of inst sits in xstn cluster cl (a register that feeds only its own xstn counts as a stage)
proc nc_loads_in_cluster {inst cl} { if {$cl eq ""} { return 0 }; foreach x [nc_load_insts $inst] { if {[nc_cluster $x] ne $cl} { return 0 } }; return 1 }
proc nc_dpin {inst} { foreach t [$inst getITerms] { if {[[$t getMTerm] getName] eq "D"} { return $t } }; return "" }
proc nc_ctr {o} { set b [$o getBBox]; return [list [expr {([$b xMin]+[$b xMax])/2}] [expr {([$b yMin]+[$b yMax])/2}]] }
# head-hop cells are sited only when each drives nothing but this chain (a buffer that also feeds another load stays put)
proc nc_headhop_single {head bs} { foreach b $bs { if {[nc_loads $b] != 1} { return 0 } }; return 1 }
# FLOW-QC-CB 11-17 (cbn_q01 setup -302.85, 147 ends): a head hop whose cells are shared (a QN inverter that feeds more than this
# chain) used to be skipped whole, so after the xstn was re-sited the inverter and the dedicated place* buffer chain behind it
# stayed at their GPL positions (1,105 um apart) and the built path was 1,740 um for a 280 um pair.  Plan for a shared head hop,
# bs nearest-first with their load counts lc: a shared cell (loads > 1) belongs to the head register and goes to the head, every
# dedicated cell (one load) is spread along the first route hop as in the unshared case.  Pure function: {{q x y} ...}.
# post-place check (report only): built head-hop path (head -> cells -> stage 0, Manhattan) over the direct head -> stage 0 distance
proc nc_hop_stretch {head stage bs} {
  global nc_hh_stretch nc_hh_seen
  lassign [nc_ctr [$head getInst]] px py; lassign [nc_ctr $stage] sx sy
  set direct [expr {abs($sx-$px)+abs($sy-$py)}]; set len 0
  foreach b [lreverse $bs] { lassign [nc_ctr $b] x y; set len [expr {$len+abs($x-$px)+abs($y-$py)}]; set px $x; set py $y }
  set len [expr {$len+abs($sx-$px)+abs($sy-$py)}]
  incr nc_hh_seen
  if {$direct > 0 && $len > 3.0*$direct} { incr nc_hh_stretch }
}
proc nc_headhop_plan {lc hx hy route hops} {
  set nb [llength $lc]; set out {}
  for {set q 0} {$q < $nb} {incr q} {
    if {[lindex $lc $q] > 1} { lappend out [list $q $hx $hy]; continue }
    set f [expr {(1.0 - double($q+1)/($nb+1)) / $hops}]
    lassign [nc_at $route $f] x y
    lappend out [list $q $x $y]
  }
  return $out
}
# join cone of candidate cell c (FLOW-QC-CB 11-17): every terminal load reached THROUGH buffers/inverters must be a member or a
# flop at its D pin (a block, other logic or an outside flop's reset/set/clock pin = not joinable); returns {c + the movable pass-through buffers} or {} when c cannot join.
proc nc_join_cone {c nx_in} {
  set cone [list $c]; set seen [dict create [$c getName] 1]; set front [list $c]; set nterm 0
  for {set d 0} {$d < 40 && [llength $front]} {incr d} {
    set nf {}
    foreach f $front { foreach o [$f getITerms] {
      if {![$o isOutputSignal] || [$o getNet] eq "NULL"} continue
      foreach l [[$o getNet] getITerms] {
        if {![$l isInputSignal]} continue
        set li [$l getInst]; set ln [$li getName]
        if {[dict exists $nx_in $ln]} { incr nterm; continue }
        if {[[$li getMaster] isBlock]} { return {} }
        if {[nc_isbuf $li]} {
          if {![nc_mov $li]} { return {} }
          if {![dict exists $seen $ln]} { dict set seen $ln 1; lappend cone $li; lappend nf $li }
        } elseif {[string match "DFF*" [[$li getMaster] getName]]} {
          # FLOW-QC-N 11-17: an OUTSIDE register reached at RESETN / SETN / CLK is a reset-relay sink, not this xstn's data
          # (cbn_q01 x_1_2: the place1438xx reset relay joined and 21 of its 22 "boundary" registers were RESETN sinks)
          if {![nc_data_pin [[$l getMTerm] getName]]} { return {} }
          incr nterm
        } else { return {} }
      }
    } }
    set front $nf
  }
  if {!$nterm || [llength $front]} { return {} }
  return $cone
}
# stretched = built path over 3x the direct distance AND more than 100 um longer (pure; lengths in dbu)
proc nc_stretched {built direct dbu} { return [expr {$direct > 0 && $built > 3.0*$direct && ($built-$direct) > 100.0*$dbu}] }
# every b_d-rooted buffer/inverter tree, to ALL its terminal loads: {paths stretched heads_with_stretch}
proc nc_tree_stretch {} {
  global nc_blk nc_dbu
  set paths 0; set bad 0; set heads 0
  foreach i [$nc_blk getInsts] {
    if {![regexp {[.]u_st[.]b_d} [$i getName]] || ![string match "DFF*" [[$i getMaster] getName]]} continue
    lassign [nc_ctr $i] hx hy; set hb 0
    foreach t [$i getITerms] { if {![$t isOutputSignal] || [$t getNet] eq "NULL"} continue
      set front [list [list [$t getNet] $hx $hy 0]]
      for {set d 0} {$d < 40 && [llength $front]} {incr d} { set nf {}
        foreach f $front { lassign $f net px py len
          foreach x [$net getITerms] { if {![$x isInputSignal]} continue
            set xi [$x getInst]; lassign [nc_ctr $xi] cx cy
            set l [expr {$len + abs($cx-$px) + abs($cy-$py)}]
            if {![[$xi getMaster] isBlock] && [nc_isbuf $xi]} {
              foreach o [$xi getITerms] { if {[$o isOutputSignal] && [$o getNet] ne "NULL"} { lappend nf [list [$o getNet] $cx $cy $l] } }
            } else {
              incr paths
              if {[nc_stretched $l [expr {abs($cx-$hx)+abs($cy-$hy)}] $nc_dbu]} { incr bad; set hb 1 }
            } } }
        set front $nf }
    }
    incr heads $hb
  }
  return [list $paths $bad $heads]
}
set nc_hh_moved 0; set nc_hh_shared 0; set nc_hh_shared_moved 0; set nc_hh_stretch 0; set nc_hh_seen 0
set nc_corefix 0; set nc_chains 0; set nc_moved 0; set nc_l0 {}; set nc_l1 {}; set nc_rc {}
proc nc_cluster {inst} { if {[regexp {^(.*)\.u_st\.} [string map {\\ {}} [$inst getName]] -> c]} { return $c }; return "" }
# one chain: walk back from the tail register $pc, spread its zero-logic stages and hop buffers along the macro-avoiding route.
# gate (CB-XSTN): empty = always; else a dict of xstn clusters, and only chains whose tail or head sits in one are spread.
proc nc_chain_one {pc {gate ""}} {
  global nc_blk nc_dbu nc_corefix nc_chains nc_moved nc_l0 nc_l1 nc_rc nc_hh_moved nc_hh_shared nc_hh_shared_moved
  # backward: hops {stage_inst bufs_on_its_D}, stages = movable fanout-1 zero-logic chain registers
  # QC-PLAN-R8 11-20: u_y_xd_* = bind relay_depth stages in front of the pipe register (+1 DECLARED cycle each); this hook is
  # their only placer (relay_mid.tcl leaves u_y_xd_ groups that feed u_pc_nk_ registers), so d<N> + xd stages split the leg evenly.
  set seq {}; set hopb {}; set cur $pc; set head ""
  while {[llength $seq] < 24} {
    set dp [nc_dpin $cur]; if {$dp eq ""} break
    lassign [nc_back $dp] drv bufs
    lappend hopb $bufs
    if {$drv eq ""} break
    set di [$drv getInst]
    set nm [string map {\\ {}} [$di getName]]
    if {![[$di getMaster] isBlock] && [string match "DFF*" [[$di getMaster] getName]] && [nc_mov $di] \
        && [regexp {(u_d[0-9]+_|u_lpad_|u_r8b_strap_|u_pd[0-9]+_|u_y_xd_)} $nm] && ![regexp {u_pc_nk_} $nm] \
        && ([nc_loads $di] == 1 || ($gate ne "" && [nc_loads_in_cluster $di [nc_cluster $pc]]))} {
      set seq [linsert $seq 0 $di]; set cur $di; continue
    }
    set head $drv; break
  }
  if {$head eq "" || ![llength $seq]} return
  if {$gate ne ""} {
    set gh [nc_cluster [$head getInst]]; set gt [nc_cluster $pc]
    if {![dict exists $gate $gh] && ![dict exists $gate $gt]} return
  }
  # head: driver flop/pin position; tail: the pipe register (anchored at the NK pin)
  if {[[[$head getInst] getMaster] isBlock]} {
    # a hard-core output launches late (NK clk->out ~870 ps TT): its first stage stays where GPL put it, next to the
    # pin (pilot8 moved it 1/5 along the route: TT -1441 at u_d3_*_t_out r[0]); the route starts at that stage
    lassign [nc_ctr [lindex $seq 0]] hx hy
    set seq [lrange $seq 1 end]
    incr nc_corefix
    if {![llength $seq]} return
  } else { lassign [nc_ctr [$head getInst]] hx hy }
  lassign [nc_ctr $pc] tx ty
  set route [nc_route_bit $hx $hy $tx $ty [$pc getName]]
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
  # CB-HEADHOP (FABLE-QC-CB 11-14): the head hop (head -> stage 0, or with a hard-core head the hop after the pin stage
  # that stays at the pin) is sited on the route too.  Left at the GPL position its inverter/buffers sat across the tile
  # from the margin-facing head (514 bits crossed a tile twice, GRT 102,780, setup -770 ps).  Hop index n-k, k = n is the
  # head hop; only the entry nearest the core (k = n+1 in the hard-core case) stays put.  A head hop whose cells are
  # shared with another load (a head-hop cell with more than one load) keeps the old rule: those cells stay where GPL put them.
  set n [llength $seq]
  set kmax [expr {min([llength $hopb], $n + 1)}]
  for {set k 0} {$k < $kmax} {incr k} {
    set bs [lindex $hopb $k]; set nb [llength $bs]; if {!$nb} continue
    set hopi [expr {$n - $k}]   ;# hop index: from position hopi to hopi+1 (sink side)
    set headhop [expr {$k == $n}]
    if {$headhop && ![nc_headhop_single $head $bs]} {
      incr nc_hh_shared
      set lc {}; foreach b $bs { lappend lc [nc_loads $b] }
      foreach pl [nc_headhop_plan $lc $hx $hy $route $hops] {
        lassign $pl q x y; set bi [lindex $bs $q]
        if {[nc_mov $bi]} { nc_put $bi $x $y; incr nc_hh_shared_moved }
      }
      nc_hop_stretch $head [lindex $seq 0] $bs
      continue
    }
    for {set q 0} {$q < $nb} {incr q} {
      set bi [lindex $bs $q]; if {![nc_mov $bi]} continue
      set f [expr {($hopi + 1 - double($q+1)/($nb+1)) / $hops}]
      if {$f < 0} { set f 0 }
      lassign [nc_at $route $f] x y; nc_put $bi $x $y
      if {$headhop} { incr nc_hh_moved }
    }
  }
  incr nc_chains
}
foreach nc_pc [$nc_blk getInsts] {
  if {![regexp {u_pc_nk_} [$nc_pc getName]] || ![string match "DFF*" [[$nc_pc getMaster] getName]]} continue
  nc_chain_one $nc_pc
}
proc nc_pct {l p} { if {![llength $l]} { return na }; set l [lsort -real $l]; return [format %.0f [lindex $l [expr {min([llength $l]-1, int([llength $l]*$p))}]]] }
puts "OT_NK_CHAIN chains $nc_chains core_head_kept $nc_corefix stages_moved $nc_moved head_hop_cells_moved $nc_hh_moved head_hop_shared_kept $nc_hh_shared bends $nc_rc max_hop_um before p50 [nc_pct $nc_l0 0.5] p90 [nc_pct $nc_l0 0.9] max [nc_pct $nc_l0 1.0] after p50 [nc_pct $nc_l1 0.5] p90 [nc_pct $nc_l1 0.9] max [nc_pct $nc_l1 1.0]"
# CB-XSTN (FABLE-QC-CB 11-14, COORD 22:5x): site each tile's xstn (u_st.*: tap_d registers, their gates and hop buffers, the
# b_d/cap/cnt/run registers) inside the strip 100 um deep outside the tile's tap face, +-100 um along the pin rows, so the
# 508 tap_d -> u_pc_nk_<tile>_tap nets do not cross the tile (cbn_q01 t13: the xstn column sat on the margin opposite the
# tap face, 441 nets over the tile; cbx t31 likewise).  The sink registers (u_pc_nk_*_tap) are the face anchors.  The D6 a_d
# pipes into and out of a moved xstn are then re-spread along their macro-avoiding route (nc_chain_one, gate = moved set).
# An xstn that already sits within the reach of its face is left alone.  OT_NK_XSTN_SITE=0 turns this off; OT_NK_XSTN_REACH_UM
# (default 100) is the strip depth.
if {![info exists ::env(OT_NK_XSTN_SITE)] || $::env(OT_NK_XSTN_SITE) ne "0"} {
set nx_reach_um 100.0
if {[info exists ::env(OT_NK_XSTN_REACH_UM)]} { set nx_reach_um $::env(OT_NK_XSTN_REACH_UM) }
set nx_reach [expr {round($nx_reach_um * $nc_dbu)}]
# cluster -> list of {pc tap_d_or_gate bufs}
set nx_sinks {}
foreach nx_pc [$nc_blk getInsts] {
  if {![regexp {u_pc_nk_u_t_[0-9]+_[0-9]+_tap[.]} [$nx_pc getName]] || ![string match "DFF*" [[$nx_pc getMaster] getName]]} continue
  set nx_dp [nc_dpin $nx_pc]; if {$nx_dp eq ""} continue
  lassign [nc_back $nx_dp] nx_drv nx_bufs
  if {$nx_drv eq ""} continue
  set nx_di [$nx_drv getInst]; if {[[$nx_di getMaster] isBlock]} continue
  set nx_cl [nc_cluster $nx_di]
  if {$nx_cl eq ""} {
    # a generic gate between the xstn registers and the pipe register: its cluster is that of its register fan-in
    foreach nx_t [$nx_di getITerms] {
      if {![$nx_t isInputSignal] || [$nx_t getNet] eq "NULL"} continue
      lassign [nc_back $nx_t] nx_d2 nx_b2
      if {$nx_d2 ne "" && ![[[$nx_d2 getInst] getMaster] isBlock]} { set nx_cl [nc_cluster [$nx_d2 getInst]]; if {$nx_cl ne ""} break }
    }
  }
  if {$nx_cl eq ""} continue
  dict lappend nx_sinks $nx_cl [list $nx_pc $nx_di $nx_bufs]
}
set nx_rst_all 0; set nx_rebuf 0; set nx_keep_ext 0; set nx_moved {}; set nx_cells 0; set nx_seen 0; set nx_kept 0; set nx_before 0.0; set nx_after 0.0
foreach nx_cl [lsort [dict keys $nx_sinks]] {
  incr nx_seen
  set nx_list [dict get $nx_sinks $nx_cl]
  set nx_x0 1e18; set nx_y0 1e18; set nx_x1 -1e18; set nx_y1 -1e18
  foreach nx_e $nx_list { lassign [nc_ctr [lindex $nx_e 0]] nx_x nx_y
    set nx_x0 [expr {min($nx_x0, $nx_x)}]; set nx_x1 [expr {max($nx_x1, $nx_x)}]; set nx_y0 [expr {min($nx_y0, $nx_y)}]; set nx_y1 [expr {max($nx_y1, $nx_y)}] }
  # the tile whose face the sink registers sit at, and the outward direction
  set nx_cx [expr {($nx_x0+$nx_x1)/2}]; set nx_cy [expr {($nx_y0+$nx_y1)/2}]
  set nx_best ""; set nx_bd 1e18
  foreach m $nc_mac { lassign $m a b c d
    set dx [expr {max($a-$nx_cx, 0, $nx_cx-$c)}]; set dy [expr {max($b-$nx_cy, 0, $nx_cy-$d)}]
    set dd [expr {$dx+$dy}]; if {$dd < $nx_bd} { set nx_bd $dd; set nx_best $m } }
  if {$nx_best eq ""} continue
  lassign $nx_best ma mb mc md
  set nx_face [lindex [lsort -index 0 -real [list [list [expr {abs($nx_cx-$ma)}] W] [list [expr {abs($nx_cx-$mc)}] E] [list [expr {abs($nx_cy-$mb)}] S] [list [expr {abs($nx_cy-$md)}] N]]] 0 1]
  switch $nx_face {
    E { set wx0 [expr {$mc + $nc_halo}]; set wx1 [expr {$mc + $nx_reach}]; set wy0 [expr {$nx_y0 - $nx_reach}]; set wy1 [expr {$nx_y1 + $nx_reach}]; set od 1; set ax x }
    W { set wx0 [expr {$ma - $nx_reach}]; set wx1 [expr {$ma - $nc_halo}]; set wy0 [expr {$nx_y0 - $nx_reach}]; set wy1 [expr {$nx_y1 + $nx_reach}]; set od -1; set ax x }
    N { set wy0 [expr {$md + $nc_halo}]; set wy1 [expr {$md + $nx_reach}]; set wx0 [expr {$nx_x0 - $nx_reach}]; set wx1 [expr {$nx_x1 + $nx_reach}]; set od 1; set ax y }
    default { set wy0 [expr {$mb - $nx_reach}]; set wy1 [expr {$mb - $nc_halo}]; set wx0 [expr {$nx_x0 - $nx_reach}]; set wx1 [expr {$nx_x1 + $nx_reach}]; set od -1; set ax y }
  }
  set wx0 [expr {max($wx0, [$nc_core xMin])}]; set wx1 [expr {min($wx1, [$nc_core xMax])}]
  set wy0 [expr {max($wy0, [$nc_core yMin])}]; set wy1 [expr {min($wy1, [$nc_core yMax])}]
  # members: every cell of the cluster, the gates between the tap registers and their pipe registers, the hop buffers
  set nx_mem {}; set nx_in [dict create]
  foreach i [$nc_blk getInsts] { if {[nc_cluster $i] eq $nx_cl && ![[$i getMaster] isBlock] && [nc_mov $i]} { lappend nx_mem $i; dict set nx_in [$i getName] 1 } }
  # the xstn's anonymous logic (generic gates and buffers between its registers): every cell next to a member whose
  # loads are all members joins it, to a fixpoint (a gate that also feeds the outside world stays where it is)
  # FLOW-QC-CB 11-17 (cbn_q01 tap_d[431/439/442/465], cap[10] at -42 .. -47.5): the join ran 4 rounds although its comment says
  # "to a fixpoint"; a buffer chain of 8-10 cells between b_d and the gate cone joins one cell per round from the member
  # side, so 4-6 cells of it stayed at their GPL positions (path 1,010-1,040 um built for 140-210 um direct, buffers 515-560
  # of ~800 ps).  The limit is now OT_NK_XSTN_JOIN_ROUNDS (default 32); the loop still stops as soon as no cell joins.
  set nx_rounds 32
  if {[info exists ::env(OT_NK_XSTN_JOIN_ROUNDS)] && [string is integer -strict $::env(OT_NK_XSTN_JOIN_ROUNDS)]} { set nx_rounds $::env(OT_NK_XSTN_JOIN_ROUNDS) }
  for {set nx_r 0} {$nx_r < $nx_rounds} {incr nx_r} {
    set nx_add {}
    foreach i $nx_mem {
      foreach t [$i getITerms] {
        set net [$t getNet]; if {$net eq "NULL" || [$net getSigType] ne "SIGNAL" || [llength [$net getITerms]] > 60} continue
        foreach u [$net getITerms] {
          set c [$u getInst]; set cn [$c getName]
          if {[dict exists $nx_in $cn] || [[$c getMaster] isBlock] || ![nc_mov $c]} continue
          if {![nc_isbuf $c] && ![regexp {^_[0-9]+_$} $cn]} continue
          # FLOW-QC-CB 11-17 (FABLE-PD-QC-0600, cbn_q01 tap_d[431/442]): the test looked at DIRECT loads only.  A trunk buffer
          # with a second branch (place164208 -> place164207 -> INV -> FIRM istation flop) failed it because its second load
          # is a buffer, and that stranded the whole relay behind it (42 heads / 81 paths).  nc_join_cone looks through
          # buffers/inverters to the terminal loads and returns the cell plus the pass-through cells that join with it.
          foreach z [nc_join_cone $c $nx_in] { set zn [$z getName]; if {![dict exists $nx_in $zn]} { dict set nx_in $zn 1; lappend nx_add $z } }
        }
      }
    }
    if {![llength $nx_add]} break
    set nx_mem [concat $nx_mem $nx_add]
  }
  foreach nx_e $nx_list { set gi [lindex $nx_e 1]; if {[nc_cluster $gi] eq "" && [nc_mov $gi]} { lappend nx_mem $gi } }
  # A xstn whose registers also drive the outside (its a_d output to a port register or any non-pipe cell across the tile)
  # would trade the 508 tap nets for those nets: count the member output nets that reach a non-member, non-pipe,
  # non-pipe-register load; more than OT_NK_XSTN_EXT_MAX (default 20) leaves the xstn where it is (needs a plan event).
  set nx_ext 0; set nx_bnd {}; set nx_rst 0
  foreach i $nx_mem { foreach t [$i getITerms] {
    if {![$t isOutputSignal] || [$t getNet] eq "NULL"} continue
    set hit 0
    foreach l [[$t getNet] getITerms] { if {![$l isInputSignal]} continue; set li [$l getInst]; set ln [$li getName]
      if {[dict exists $nx_in $ln] || [regexp {u_pc_nk_|u_d[0-9]+_} $ln]} continue
      # FLOW-QC-N 11-17: a boundary register is one the xstn reaches at its D pin; reset / set / clock sinks are counted apart
      if {[string match "DFF*" [[$li getMaster] getName]]} { if {[nc_data_pin [[$l getMTerm] getName]]} { lappend nx_bnd $li } else { incr nx_rst }; continue }
      if {[nc_isbuf $li] && ![[$li getMaster] isBlock]} { set bo 0
        foreach xt [nc_load_terms $li] { set xi [$xt getInst]; set xn [$xi getName]
          if {[dict exists $nx_in $xn] || [regexp {u_pc_nk_|u_d[0-9]+_} $xn]} continue
          if {[string match "DFF*" [[$xi getMaster] getName]]} { if {[nc_data_pin [[$xt getMTerm] getName]]} { lappend nx_bnd $xi } else { incr nx_rst }; continue }
          set bo 1 }
        if {!$bo} continue }
      set hit 1 }
    incr nx_ext $hit } }
  set nx_ext_max 20; if {[info exists ::env(OT_NK_XSTN_EXT_MAX)]} { set nx_ext_max $::env(OT_NK_XSTN_EXT_MAX) }
  # a register outside the xstn that it feeds (the die output pipe) keeps a single hop: refuse when the strip is farther than 405 um from it
  set nx_bmax 0.0
  foreach b $nx_bnd { lassign [nc_ctr $b] bx by
    set dd [expr {(max($wx0-$bx, 0, $bx-$wx1) + max($wy0-$by, 0, $by-$wy1))/double($nc_dbu)}]; set nx_bmax [expr {max($nx_bmax, $dd)}] }
  if {$nx_bmax > 405.0} { set nx_ext [expr {$nx_ext + 1000000}] }
  incr nx_rst_all $nx_rst
  if {$nx_ext > $nx_ext_max} { puts "OT_XSTN_KEEP $nx_cl face $nx_face external_nets $nx_ext > $nx_ext_max boundary_reg_um [format %.0f $nx_bmax] reset_sinks_excluded $nx_rst (an output of the xstn leaves across the tile; plan event needed)"; incr nx_keep_ext; continue }
  # distance of a cell to the strip (0 inside)
  set nx_far {}
  foreach i $nx_mem { lassign [nc_ctr $i] x y
    lappend nx_far [expr {(max($wx0-$x, 0, $x-$wx1) + max($wy0-$y, 0, $y-$wy1))/double($nc_dbu)}] }
  set nx_q [lindex [lsort -real $nx_far] [expr {min([llength $nx_far]-1, int([llength $nx_far]*0.9))}]]
  set nx_before [expr {max($nx_before, $nx_q)}]
  if {$nx_q <= 25.0 || !([llength $nx_mem])} { incr nx_kept; continue }
  # tap registers / gates go next to their pipe register; everything else fills the strip in rows, ordered by current y
  set nx_tap {}
  foreach nx_e $nx_list { lassign $nx_e pc gi bufs
    lassign [nc_ctr $pc] px py
    if {$ax eq "x"} { set tx [expr {$px + $od*12*$nc_dbu}]; set ty $py } else { set tx $px; set ty [expr {$py + $od*12*$nc_dbu}] }
    if {[nc_mov $gi]} { nc_put $gi $tx $ty; incr nx_cells; dict set nx_tap $gi 1 }
    # the gate's own fan-in registers: tap_d flops feeding a gate stay with the gate (below); hop buffers midway
    foreach bi $bufs { if {[nc_mov $bi]} { nc_put $bi [expr {($px+$tx)/2}] [expr {($py+$ty)/2}]; incr nx_cells; dict set nx_tap $bi 1 } }
  }
  set nx_rest {}
  foreach i $nx_mem { if {![dict exists $nx_tap $i]} { lappend nx_rest $i } }
  set nx_pitch [expr {int(2.0*$nc_dbu)}]
  set nx_w [expr {$wx1-$wx0}]; set nx_h [expr {$wy1-$wy0}]
  set nx_cols [expr {max(1, int(sqrt(double([llength $nx_rest]) * $nx_pitch * $nx_w / max(1.0, double($nx_h)) / $nx_pitch)))}]
  set nx_k 0
  foreach i [lsort -command {apply {{a b} {expr {[lindex [nc_ctr $a] 1] - [lindex [nc_ctr $b] 1]}}}} $nx_rest] {
    set cx [expr {$nx_k % $nx_cols}]; set ry [expr {$nx_k / $nx_cols}]
    if {$ax eq "x"} {
      set x [expr {($od > 0 ? $wx0 + $cx*$nx_pitch : $wx1 - $cx*$nx_pitch)}]; set y [expr {$wy0 + $ry*$nx_pitch}]
      if {$y > $wy1} { set y [expr {$wy0 + ($ry % max(1, $nx_h/$nx_pitch))*$nx_pitch}] }
    } else {
      set y [expr {($od > 0 ? $wy0 + $cx*$nx_pitch : $wy1 - $cx*$nx_pitch)}]; set x [expr {$wx0 + $ry*$nx_pitch}]
      if {$x > $wx1} { set x [expr {$wx0 + ($ry % max(1, $nx_w/$nx_pitch))*$nx_pitch}] }
    }
    nc_put $i $x $y; incr nx_cells; incr nx_k
  }
  # FLOW-QC-N 11-17 (FABLE-FIX-QC-N, cbn_q01 n1b x_1_3 b_d[383]): the fill orders the cells by their old y and wraps the
  # column over the whole strip width, so a buffer/inverter landed in a column unrelated to its driver and loads (INV 51.5 um
  # east of both: 147.5 um built for a 44.4 um pair, the one stretched b_d path that stopped the kit).  Second pass: every
  # filled buffer/inverter goes to the coordinate-wise median of its driver and its direct loads, inside the strip.
  for {set nx_r 0} {$nx_r < 2} {incr nx_r} {
    foreach i $nx_rest {
      if {![nc_isbuf $i]} continue
      set nx_pts [nc_buf_neigh $i]; if {[llength $nx_pts] < 2} continue
      lassign [nc_median_pt $nx_pts] x y
      lassign [nc_clamp_box $x $y $wx0 $wy0 $wx1 $wy1] x y
      nc_put $i $x $y; if {!$nx_r} { incr nx_rebuf }
    }
  }
  set nx_far {}
  foreach i $nx_mem { lassign [nc_ctr $i] x y
    lappend nx_far [expr {(max($wx0-$x, 0, $x-$wx1) + max($wy0-$y, 0, $y-$wy1))/double($nc_dbu)}] }
  set nx_after [expr {max($nx_after, [lindex [lsort -real $nx_far] [expr {min([llength $nx_far]-1, int([llength $nx_far]*0.9))}]])}]
  dict set nx_moved $nx_cl $nx_face
}
set nx_spread 0
if {[dict size $nx_moved]} {
  set nc_chains_before $nc_chains
  foreach i [$nc_blk getInsts] {
    if {![regexp {[.]u_st[.]b_d} [$i getName]] || ![string match "DFF*" [[$i getMaster] getName]]} continue
    nc_chain_one $i $nx_moved
  }
  set nx_spread [expr {$nc_chains - $nc_chains_before}]
}
puts "OT_XSTN_SITE xstn $nx_seen kept $nx_kept kept_external $nx_keep_ext moved [dict size $nx_moved] cells_moved $nx_cells p90_um_from_face_strip_before [format %.0f $nx_before] after [format %.0f $nx_after] reach_um $nx_reach_um a_d_chains_spread $nx_spread faces [dict values $nx_moved] fill_bufs_resited $nx_rebuf reset_sinks_excluded $nx_rst_all"
catch {puts "OT_NK_HEADHOP_RESITE shared_hops $nc_hh_shared shared_hop_cells_resited $nc_hh_shared_moved shared_hops_checked $nc_hh_seen path_over_3x_direct_after $nc_hh_stretch"}
# FLOW-QC-CB 11-17 (FABLE-PD-QC-0600): the check above counts shared head hops only and printed 0 with 81 stretched b_d paths
# present.  Count every b_d-rooted buffer tree to all its terminal loads and stop at 3_4 (before repair_design) when the count is
# above OT_NK_STRETCH_MAX (default 0).  OT_NK_STRETCH_STOP=0 reports without stopping.
if {[dict size $nx_moved] || [info exists ::env(OT_NK_STRETCH_ALWAYS)]} {
  lassign [nc_tree_stretch] nx_sp nx_sb nx_sh
  puts "OT_XSTN_STRETCH b_d_paths $nx_sp stretched_over_3x_and_100um $nx_sb heads $nx_sh"
  if {$nx_sb > 0 && (![info exists ::env(OT_NK_STRETCH_STOP)] || $::env(OT_NK_STRETCH_STOP) ne "1")} { puts "OT_XSTN_STRETCH ADVISORY $nx_sb stretched b_d paths (not a stop; OT_NK_STRETCH_STOP=1 stops)" }
  set nx_smax 0; if {[info exists ::env(OT_NK_STRETCH_MAX)]} { set nx_smax $::env(OT_NK_STRETCH_MAX) }
  # SONNET-FIX-QC 11-19 (OWNER r703 11-18 no stops; academic profile 11-13: blocking gates are DRC0 route, setup, hold, bind): the stretch
  # count is REPORTED by default (cbn_q11 cl5cc92dfe 147 / cl49ae4555 132 of ~2,700 b_d paths stopped both kits at 3_4 before any
  # timing was read).  OT_NK_STRETCH_STOP=1 restores the stop.
  if {$nx_sb > $nx_smax && [info exists ::env(OT_NK_STRETCH_STOP)] && $::env(OT_NK_STRETCH_STOP) eq "1"} {
    error "OT_XSTN_STRETCH stretched b_d paths $nx_sb > $nx_smax (heads $nx_sh of $nx_sp paths): a b_d buffer tree is longer than 3x its direct distance; fix the siting, do not repair"
  }
}
}
# CBF-R8-CORRIDOR: an INNER strap bank has a fixed common prefix, a selectable count bank and a final NK pipe.
# The mux is not a register chain: discover it by the kept bank identity, then verify ALL dynamic cone roots.
# Opt-in until the coherent extra PIN-cycle event and its PLACE pilot are accepted. No netlist/latency changes here.
if {[info exists ::env(OT_NK_R8_COUNT_CHAIN)] && $::env(OT_NK_R8_COUNT_CHAIN) eq "1"} {
proc nc_cnt_name {inst} { return [string map {\\ {}} [$inst getName]] }
proc nc_cnt_data_cone {it allowed} {
  set todo [list [$it getNet]]; set seen {}; set roots {}; set gates {}; set static {}; set bad {}
  for {set depth 0} {$depth < 80 && [llength $todo]} {incr depth} {
    set more {}
    foreach net $todo {
      if {$net eq "NULL" || $net eq "" || [dict exists $seen $net]} continue
      dict set seen $net 1
      foreach bt [$net getBTerms] {
        if {![string match "*strap_r8pad_*" [$bt getName]]} { lappend bad "non-count port [$bt getName]" } else { lappend static [$bt getName] }
      }
      foreach drv [$net getITerms] {
        if {![$drv isOutputSignal]} continue
        set di [$drv getInst]; set nm [nc_cnt_name $di]; set mn [[$di getMaster] getName]
        if {[dict exists $allowed $nm]} { dict set roots $nm $di; continue }
        if {[[$di getMaster] isBlock] || [string match "DFF*" $mn] || [string match "*LATCH*" $mn]} { lappend bad "unexpected data root $nm"; continue }
        if {[string match "TIE*" $mn] || [string match "*TIE*" $mn]} continue
        dict set gates $nm $di
        foreach ip [$di getITerms] { if {[$ip isInputSignal] && [$ip getNet] ne "NULL" && [[$ip getNet] getSigType] eq "SIGNAL"} { lappend more [$ip getNet] } }
      }
    }
    set todo $more
  }
  if {[llength $todo]} { lappend bad "count cone exceeds 80 logic levels" }
  return [list $roots $gates $static $bad]
}
# Keep shared static count-decode cells in their existing tree. Move only gates carrying this bit's data.
proc nc_cnt_dynamic_gates {roots gates} {
  set nets {}; set selected {}
  foreach nm [dict keys $roots] { foreach t [[dict get $roots $nm] getITerms] { if {[$t isOutputSignal] && [$t getNet] ne "NULL"} { dict set nets [$t getNet] 1 } } }
  for {set pass 0} {$pass < 80} {incr pass} {
    set changed 0
    foreach nm [dict keys $gates] {
      if {[dict exists $selected $nm]} continue
      set i [dict get $gates $nm];set data 0
      foreach t [$i getITerms] { if {[$t isInputSignal] && [dict exists $nets [$t getNet]]} { set data 1 } }
      if {!$data} continue
      dict set selected $nm $i;set changed 1
      foreach t [$i getITerms] { if {[$t isOutputSignal] && [$t getNet] ne "NULL"} { dict set nets [$t getNet] 1 } }
    }
    if {!$changed} break
  }
  return $selected
}
proc nc_cnt_route_ok {pts} {
  for {set j 1} {$j < [llength $pts]} {incr j} { lassign [lindex $pts [expr {$j-1}]] a b; lassign [lindex $pts $j] c d; if {$a != $c && $b != $d} { return 0 } }
  return [nc_ok $pts]
}
proc nc_cnt_layout {route fixed span dbu} {
  if {$fixed < 2 || $span < 1 || $span > 16 || ![nc_cnt_route_ok $route]} { error "invalid count-bank corridor" }
  set hop [expr {[nc_len $route]/double($fixed)/$dbu}]
  if {$hop > 405.0} { error "NEED_PIN_CYCLE fixed=$fixed min_count_hop_um=$hop" }
  set fs {};set cs {}
  for {set j 1} {$j < $fixed} {incr j} { lappend fs [nc_at $route [expr {double($j)/$fixed}]] }
  for {set j 0} {$j < $span} {incr j} { lappend cs [nc_at $route [expr {(double($fixed-1)+double($j+1)/($span+1))/$fixed}]] }
  return [dict create max_hop_um $hop fixed $fs count $cs]
}
# Validate every bit before applying ANY of this pass's locations. An under-staged site cannot partially route.
proc nc_cnt_place {inst x y} { global nc_cnt_targets;dict set nc_cnt_targets $inst [list $x $y] }
set nc_cnt_targets {}
# Full banks need row area, not 514 near-coincident points on a route skeleton.
# Per-stage rectangles reserve conservative row demand; the final count/mux bank is shared
# so its data muxes cannot overlap the optional FF bank. Legalization remains mandatory.
proc nc_cnt_bank_add {group inst} { global nc_cnt_bank_groups;dict set nc_cnt_bank_groups $group $inst 1 }
proc nc_cnt_bank_grid {members targets dbu} {
  global nc_mac nc_core nc_halo
  set n [llength $members];set sx 0;set sy 0;set mw 0;set mh 0;set area 0
  foreach i $members {
    lassign [dict get $targets $i] x y;set sx [expr {$sx+$x}];set sy [expr {$sy+$y}]
    set m [$i getMaster];set w [$m getWidth];set h [$m getHeight]
    set mw [expr {max($mw,$w)}];set mh [expr {max($mh,$h)}];set area [expr {$area+$w*$h}]
  }
  set cols [expr {min(27,$n)}];set rows [expr {int(ceil(double($n)/$cols))}]
  set px [expr {$mw*1.25}];set py [expr {$mh*2.25}]
  set w [expr {($cols-1)*$px+$mw}];set h [expr {($rows-1)*$py+$mh}]
  set x [expr {$sx/double($n)-$w/2}];set y [expr {$sy/double($n)-$h/2}]
  set xs [list $x];set ys [list $y]
  foreach m $nc_mac {lassign $m a b c d;lappend xs [expr {$a-$nc_halo-$w}] [expr {$c+$nc_halo}];lappend ys [expr {$b-$nc_halo-$h}] [expr {$d+$nc_halo}]}
  set best {};set dist 1e100
  foreach xx $xs {foreach yy $ys {
    if {$xx<[$nc_core xMin] || $yy<[$nc_core yMin] || $xx+$w>[$nc_core xMax] || $yy+$h>[$nc_core yMax]} continue
    set ok 1;foreach m $nc_mac {lassign $m a b c d;if {$xx<$c+$nc_halo && $xx+$w>$a-$nc_halo && $yy<$d+$nc_halo && $yy+$h>$b-$nc_halo} {set ok 0;break}}
    set dd [expr {abs($xx-$x)+abs($yy-$y)}]
    if {$ok && $dd<$dist} {set best [list $xx $yy];set dist $dd}
  }}
  if {$best eq {} || $dist/double($dbu)>60.0} {error "bank rectangle cannot fit near corridor"}
  lassign $best x y;set out {};set k 0
  foreach i $members {dict set out $i [list [expr {$x+($k%$cols)*$px}] [expr {$y+int($k/$cols)*$py}]];incr k}
  return [dict create targets $out bbox [list $x $y [expr {$x+$w}] [expr {$y+$h}]] rows $rows occupancy [expr {$area/double($w*$h)}]]
}
set nc_cnt_bank_groups {};set nc_cnt_bit_paths {}
proc nc_cnt_hop_buffers {sink fa fb route} {
  set dp [nc_dpin $sink]; if {$dp eq ""} return
  lassign [nc_back $dp] _ bs; set n [llength $bs]
  for {set q 0} {$q < $n} {incr q} {
    set bi [lindex $bs $q]; if {![nc_mov $bi]} continue
    set f [expr {$fb - ($fb-$fa)*double($q+1)/($n+1)}]
    lassign [nc_at $route $f] x y; nc_cnt_place $bi $x $y
  }
}
proc nc_cnt_parse_name {nm} {
  if {[regexp {^(.*u_r8b_(strap_r8pad_.+)_f)[./]r\[([0-9]+)\]\[([0-9]+)\]} $nm _ bank site st bit]} { return [list fixed $bank $st $bit] }
  if {[regexp {^(.*u_r8b_(strap_r8pad_.+)_f)[./]q\[([0-9]+)\]} $nm _ bank site bit]} { return [list fixedq $bank -1 $bit] }
  if {[regexp {^(.*u_r8b_(strap_r8pad_.+))[./]r\[([0-9]+)\]\[([0-9]+)\]} $nm _ bank site st bit] && ![string match "*_f" $bank]} { return [list count $bank $st $bit] }
  if {[regexp {^(.*u_pc_nk_.+)[./](?:r\[0\]\[|q\[)([0-9]+)\]} $nm _ bank bit]} { return [list pc $bank 0 $bit] }
  return {}
}
set nc_cnt_all {}; set nc_cnt_fixed {}; set nc_cnt_fixed_q {}; set nc_cnt_count {}; set nc_cnt_pc {}
foreach i [$nc_blk getInsts] {
  if {![string match "DFF*" [[$i getMaster] getName]]} continue
  set nm [nc_cnt_name $i]; dict set nc_cnt_all $nm $i
  set parsed [nc_cnt_parse_name $nm];if {![llength $parsed]} continue
  lassign $parsed kind bank st bit
  switch $kind {
    fixed { dict set nc_cnt_fixed $bank $bit $st $i }
    fixedq { dict set nc_cnt_fixed_q $bank $bit $i }
    count { dict set nc_cnt_count $bank $bit $st $i }
    pc { dict set nc_cnt_pc $bank $bit $i }
  }
}
# Yosys aliases the LAST fixed register to q[bit] (and the one-stage input pipe likewise). Include that stage.
foreach bank [dict keys $nc_cnt_fixed_q] {
  foreach bit [dict keys [dict get $nc_cnt_fixed_q $bank]] {
    set j 0
    if {[dict exists $nc_cnt_fixed $bank $bit]} { set j [dict size [dict get $nc_cnt_fixed $bank $bit]] }
    dict set nc_cnt_fixed $bank $bit $j [dict get $nc_cnt_fixed_q $bank $bit]
  }
}
set nc_cnt_chains 0; set nc_cnt_stages 0; set nc_cnt_mux 0; set nc_cnt_refused 0; set nc_cnt_worst 0; set nc_cnt_seen 0
foreach bank [dict keys $nc_cnt_fixed] {
  if {[info exists ::env(OT_NK_R8_COUNT_SITE_REGEX)] && ![regexp $::env(OT_NK_R8_COUNT_SITE_REGEX) $bank]} continue
  if {![regexp {^(.*)u_r8b_strap_r8pad_(u_t_[0-9]+_[0-9]+)_(n_[ab])_in[0-9]*_f$} $bank _ scope rel port]} continue
  set countbank [string range $bank 0 end-2]; set pcbank ${scope}u_pc_nk_${rel}_${port}
  foreach bit [dict keys [dict get $nc_cnt_fixed $bank]] {
    incr nc_cnt_seen
    set fixed [dict get $nc_cnt_fixed $bank $bit]; set n [dict size $fixed]
    if {$n < 2 || ![dict exists $nc_cnt_pc $pcbank $bit] || ![dict exists $nc_cnt_count $countbank $bit]} { incr nc_cnt_refused; continue }
    set counts [dict get $nc_cnt_count $countbank $bit]; set span [dict size $counts]; set seq {}; set good 1
    for {set j 0} {$j < $n} {incr j} { if {![dict exists $fixed $j]} { set good 0; break }; lappend seq [dict get $fixed $j] }
    for {set j 0} {$j < $span} {incr j} { if {![dict exists $counts $j]} { set good 0; break } }
    if {!$good || $span < 1 || $span > 16} { incr nc_cnt_refused; continue }
    set first [lindex $seq 0]; set pc [dict get $nc_cnt_pc $pcbank $bit]
    # The improved core_input_anchor must have identified this real PC (including its generic QN inverter).
    # Its face-file identity survives release to PLACED before this hook; a floating old PC is not an endpoint.
    if {![dict exists $nc_face [$pc getName]]} {
      if {$nc_cnt_refused < 8} { puts "OT_NK_R8_COUNT_REFUSE bank $bank bit $bit missing_verified_core_input_anchor" }
      incr nc_cnt_refused;continue
    }
    # The hard source's first output register is the existing core_out_land anchor. Never move it or the input pipe.
    lassign [nc_back [nc_dpin $first]] source _
    if {$source eq "" || ![[[$source getInst] getMaster] isBlock]} { incr nc_cnt_refused; continue }
    set source_box [$source getBBox]
    lassign [nc_ctr $first] first_x first_y
    set source_gap [expr {(abs($first_x-([$source_box xMin]+[$source_box xMax])/2)+abs($first_y-([$source_box yMin]+[$source_box yMax])/2))/double($nc_dbu)}]
    if {$source_gap > 30.0} {
      if {$nc_cnt_refused < 8} { puts "OT_NK_R8_COUNT_REFUSE bank $bank bit $bit missing_verified_output_anchor gap_um $source_gap" }
      incr nc_cnt_refused;continue
    }
    set allowed [dict create [nc_cnt_name [lindex $seq end]] [lindex $seq end]]
    foreach j [dict keys $counts] { set ci [dict get $counts $j]; dict set allowed [nc_cnt_name $ci] $ci }
    lassign [nc_cnt_data_cone [nc_dpin $pc] $allowed] roots gates static bad
    if {[llength $bad] || [dict size $roots] != [dict size $allowed]} { incr nc_cnt_refused; continue }
    # Each optional-count register must itself be the actual serial chain fed from the fixed prefix.
    set previous [lindex $seq end]
    for {set j 0} {$j < $span} {incr j} {
      set ci [dict get $counts $j]; lassign [nc_back [nc_dpin $ci]] drv _
      if {$drv eq "" || [$drv getInst] ne $previous} { set good 0; break }; set previous $ci
    }
    if {!$good} { incr nc_cnt_refused; continue }
    lassign [nc_ctr $first] hx hy; lassign [nc_ctr $pc] tx ty
    set route [nc_route $hx $hy $tx $ty]; set hop [expr {[nc_len $route]/double($n)/$nc_dbu}]
    if {[catch {set layout [nc_cnt_layout $route $n $span $nc_dbu]} layout_error]} {
      if {$nc_cnt_refused < 8} { puts "OT_NK_R8_COUNT_REFUSE bank $bank bit $bit fixed $n count_span $span route_um [expr {[nc_len $route]/double($nc_dbu)}] min_count_hop_um $hop NEED_PIN_CYCLE" }
      incr nc_cnt_refused; continue
    }
    # Refuse conflicting firm sites; this pass never overrides a declared immutable placement.
    foreach i [lrange $seq 1 end] { if {![nc_mov $i]} { set good 0 } }
    foreach j [dict keys $counts] { if {![nc_mov [dict get $counts $j]]} { set good 0 } }
    if {!$good} { incr nc_cnt_refused; continue }
    for {set j 1} {$j < $n} {incr j} {
      set i [lindex $seq $j]; lassign [lindex [dict get $layout fixed] [expr {$j-1}]] x y; nc_cnt_place $i $x $y;nc_cnt_bank_add ${bank}:fixed$j $i
      nc_cnt_hop_buffers $i [expr {double($j-1)/$n}] [expr {double($j)/$n}] $route
      incr nc_cnt_stages
    }
    for {set j 0} {$j < $span} {incr j} {
      set f [expr {(double($n-1)+double($j+1)/($span+1))/$n}]
      set i [dict get $counts $j]; lassign [lindex [dict get $layout count] $j] x y; nc_cnt_place $i $x $y;nc_cnt_bank_add ${bank}:count_mux $i
      set prevf [expr {(double($n-1)+double($j)/($span+1))/$n}]
      nc_cnt_hop_buffers $i $prevf $f $route; incr nc_cnt_stages
    }
    # Count decode/mux and its buffers sit inside the final fixed->input hop. Quasi-static strap inputs remain pins.
    set gates [nc_cnt_dynamic_gates $roots $gates]
    set ng [dict size $gates]; set gi 0
    foreach nm [lsort [dict keys $gates]] {
      set i [dict get $gates $nm]; incr gi
      if {[nc_mov $i]} { set gf [expr {(double($n-1)+0.2+0.6*double($gi)/($ng+1))/$n}]; lassign [nc_at $route $gf] x y; nc_cnt_place $i $x $y;nc_cnt_bank_add ${bank}:count_mux $i; incr nc_cnt_mux }
    }
    set countseq {};foreach j [lsort -integer [dict keys $counts]] {lappend countseq [dict get $counts $j]}
    lappend nc_cnt_bit_paths [list $seq $countseq $pc]
    set nc_cnt_worst [expr {max($nc_cnt_worst,$hop)}]; incr nc_cnt_chains
  }
}
if {$nc_cnt_refused} {
  puts "OT_NK_R8_COUNT_BLOCKED eligible_bits $nc_cnt_seen planned_bits $nc_cnt_chains placed_bits 0 refused_bits $nc_cnt_refused"
  error "CBF count-bank corridor requires a coherent PIN-cycle/site event; no locations from this pass applied"
}
set nc_cnt_rects {};set nc_cnt_bank_report {};set nc_cnt_inst_bank {}
foreach group [dict keys $nc_cnt_bank_groups] {
  set members [lsort -command {apply {{a b} {string compare [$a getName] [$b getName]}}} [dict keys [dict get $nc_cnt_bank_groups $group]]]
  set z [nc_cnt_bank_grid $members $nc_cnt_targets $nc_dbu]
  lassign [dict get $z bbox] a b c d
  foreach prev [dict keys $nc_cnt_rects] {
    lassign [dict get $nc_cnt_rects $prev] aa bb cc dd
    if {$a<$cc && $c>$aa && $b<$dd && $d>$bb} {error "overlapping corridor bank rectangles: $group $prev"}
  }
  dict set nc_cnt_rects $group [dict get $z bbox]
  foreach i [dict keys [dict get $z targets]] {dict set nc_cnt_targets $i [dict get $z targets $i];dict set nc_cnt_inst_bank $i $group}
  lappend nc_cnt_bank_report [list $group [llength $members] [dict get $z rows] [dict get $z occupancy] [dict get $z bbox]]
}
proc nc_cnt_target_ctr {inst} {global nc_cnt_targets;if {[dict exists $nc_cnt_targets $inst]} {return [dict get $nc_cnt_targets $inst]};return [nc_ctr $inst]}
proc nc_cnt_envelope {inst} {
  global nc_cnt_inst_bank nc_cnt_rects
  if {![dict exists $nc_cnt_inst_bank $inst]} {return [list [nc_cnt_target_ctr $inst]]}
  lassign [dict get $nc_cnt_rects [dict get $nc_cnt_inst_bank $inst]] a b c d
  return [list [list $a $b] [list $a $d] [list $c $b] [list $c $d]]
}
set nc_cnt_spread_worst 0;set nc_cnt_envelope_worst 0;set nc_cnt_pair_seen {}
foreach bitpath $nc_cnt_bit_paths {
  lassign $bitpath fs cs pc
  # Both the minimum-count bypass and every selected-count serial hop must fit.
  set pairs {};set prev [lindex $fs 0]
  foreach i [concat [lrange $fs 1 end] [list $pc]] {lappend pairs [list $prev $i];set prev $i}
  set prev [lindex $fs end];foreach i [concat $cs [list $pc]] {lappend pairs [list $prev $i];set prev $i}
  foreach pair $pairs {
    lassign $pair src dst;lassign [nc_cnt_target_ctr $src] hx hy;lassign [nc_cnt_target_ctr $dst] tx ty
    set route [nc_route $hx $hy $tx $ty];set hop [expr {[nc_len $route]/double($nc_dbu)}]
    if {![nc_cnt_route_ok $route] || $hop>405.0} {error "bank spread exceeds macro-clear hop bound: $hop um"}
    set nc_cnt_spread_worst [expr {max($nc_cnt_spread_worst,$hop)}]
    set sk $src;set dk $dst
    if {[dict exists $nc_cnt_inst_bank $src]} {set sk [dict get $nc_cnt_inst_bank $src]}
    if {[dict exists $nc_cnt_inst_bank $dst]} {set dk [dict get $nc_cnt_inst_bank $dst]}
    if {![dict exists $nc_cnt_pair_seen [list $sk $dk]]} {
      dict set nc_cnt_pair_seen [list $sk $dk] 1
      foreach sp [nc_cnt_envelope $src] {foreach dp [nc_cnt_envelope $dst] {
        lassign $sp x y;lassign $dp xx yy;set er [nc_route $x $y $xx $yy];set eh [expr {[nc_len $er]/double($nc_dbu)}]
        if {![nc_cnt_route_ok $er] || $eh>405.0} {error "bank corner envelope exceeds macro-clear hop bound: $eh um"}
        set nc_cnt_envelope_worst [expr {max($nc_cnt_envelope_worst,$eh)}]
      }}
    }
  }
}
foreach row $nc_cnt_bank_report {puts "OT_NK_R8_BANK group_cells_rows_occupancy_bbox_dbu $row"}
puts "OT_NK_R8_BANK_HOPS max_um $nc_cnt_spread_worst rectangle_corner_envelope_um $nc_cnt_envelope_worst"
foreach inst [dict keys $nc_cnt_targets] { lassign [dict get $nc_cnt_targets $inst] x y;nc_put $inst $x $y }
puts "OT_NK_R8_COUNT_CHAIN eligible_bits $nc_cnt_seen placed_bits $nc_cnt_chains stages_moved $nc_cnt_stages mux_cells_moved $nc_cnt_mux refused_bits $nc_cnt_refused min_count_max_hop_um $nc_cnt_worst"
}
}
# R8-CORE-SEAT (FABLE-FIX-QC-STRAP 11-21, FABLE-CLOSURE lever 6 "first-hop seats at core pin faces"; opt-in OT_R8_CORE_SEAT=1
# from plan budgets.r_r8_core_seat, unset = this block does not run and the kit is byte-identical in behaviour).
# Class (QC slw_st_a_v2__cl9f076a5c a3, measured): an R8 strap pad (bind: fixed pad ot_dp_dly u_r8b_<site>_f, count bank
# ot_dp_dly_cnt u_r8b_<site>, combinational tap mux) sits between an in-boundary register and a HARD-CORE input pin.  GPL is
# indifferent to where a fanout-1 chain sits, so the stages bunch near the head and the last flop drives the core pin over the
# whole distance (u_r0 rs_n_c_p: 5 stages inside 80 um of the head, last hop 1,067 um, -169.05 ps post-hook CTS, 43 GRT
# endpoints; rs_n_hi / lo: last hop 418 to 439 um).  The NK count pass above handles only pads that end on a u_pc_nk register.
# Rule: for every hard-core input pin whose data cone (through gates, to the first flops) holds only R8 pad flops and static
# strap inputs, and whose farthest cone flop is more than OT_R8_SEAT_TAIL_UM (40) away:
#   - the cone flops (last fixed stage, count stages) and the gates that carry their data sit at the pin, just outside the
#     core face (count stages nearest, last fixed stage behind them; a flop shared by several pins sits at their median);
#   - the earlier fixed stages (fanout-1 chain behind the last fixed stage) and their hop buffers are spread at equal
#     fractions of the macro-avoiding route head -> seat (nc_route), like nc_chain_one does for a pipe register tail.
# No netlist change, no cycle; FIRM / plan-sited cells are never moved.  DPL legalizes.  A chain whose equal hop is over 405 um
# is still spread and counted need_stage (a plan item: +1 pad stage).  A pin whose cone flops already sit at the pin keeps them;
# its fixed chain is still spread when one of its hops is over OT_R8_SEAT_HOP_UM (300).
if {[info exists ::env(OT_R8_CORE_SEAT)] && $::env(OT_R8_CORE_SEAT) eq "1"} {
uplevel #0 {
set rs_tail_um 40.0; if {[info exists ::env(OT_R8_SEAT_TAIL_UM)] && [string is double -strict $::env(OT_R8_SEAT_TAIL_UM)]} { set rs_tail_um $::env(OT_R8_SEAT_TAIL_UM) }
set rs_hop_thr 300.0; if {[info exists ::env(OT_R8_SEAT_HOP_UM)] && [string is double -strict $::env(OT_R8_SEAT_HOP_UM)]} { set rs_hop_thr $::env(OT_R8_SEAT_HOP_UM) }
set rs_root_re {u_r8b_strap_r8pad_}; if {[info exists ::env(OT_R8_SEAT_ROOT_RE)] && $::env(OT_R8_SEAT_ROOT_RE) ne ""} { set rs_root_re $::env(OT_R8_SEAT_ROOT_RE) }
proc rs_name {i} { return [string map {\\ {}} [$i getName]] }
proc rs_isff {i} { return [string match "DFF*" [[$i getMaster] getName]] }
# data cone of an input pin back to the first flops: {roots (name -> inst) gates (insts, nearest first) ok}
proc rs_cone {it} {
  set roots {}; set gates {}; set seen {}; set front [list $it]; set ok 1
  for {set d 0} {$d < 24 && [llength $front]} {incr d} {
    set nf {}
    foreach t $front {
      set net [$t getNet]; if {$net eq "NULL" || $net eq ""} continue
      if {[$net getSigType] ne "SIGNAL"} continue
      set bts [$net getBTerms]
      if {[llength $bts]} { foreach bt $bts { if {![regexp {^strap_} [$bt getName]]} { set ok 0 } }; continue }
      set drv ""; foreach o [$net getITerms] { if {[$o isOutputSignal]} { set drv $o } }
      if {$drv eq ""} continue
      set di [$drv getInst]; set dn [$di getName]; set dm [[$di getMaster] getName]
      if {[[$di getMaster] isBlock] || [regexp {^(DLL|DHL|ICG|SDF)} $dm]} { set ok 0; continue }
      if {[rs_isff $di]} { dict set roots $dn $di; continue }
      if {[dict exists $seen $dn]} continue
      dict set seen $dn 1; lappend gates $di
      if {[llength $gates] > 64} { return [list {} {} 0] }
      foreach x [$di getITerms] { if {[$x isInputSignal]} { lappend nf $x } }
    }
    set front $nf
  }
  if {[llength $front]} { set ok 0 }
  return [list $roots $gates $ok]
}
# the gates of a cone that carry a root's data (static strap decode stays where it is: it is shared by the bank)
proc rs_dynamic {roots gates} {
  set nets {}; set sel {}
  dict for {nm i} $roots { foreach t [$i getITerms] { if {[$t isOutputSignal] && [$t getNet] ne "NULL"} { dict set nets [$t getNet] 1 } } }
  for {set pass 0} {$pass < 80} {incr pass} {
    set ch 0
    foreach g $gates {
      set gn [$g getName]; if {[dict exists $sel $gn]} continue
      set dyn 0; foreach t [$g getITerms] { if {[$t isInputSignal] && [$t getNet] ne "NULL" && [dict exists $nets [$t getNet]]} { set dyn 1 } }
      if {!$dyn} continue
      dict set sel $gn $g; set ch 1
      foreach t [$g getITerms] { if {[$t isOutputSignal] && [$t getNet] ne "NULL"} { dict set nets [$t getNet] 1 } }
    }
    if {!$ch} break
  }
  return $sel
}
proc rs_out {x y} {
  global nc_mac nc_halo
  foreach m $nc_mac {
    lassign $m a b c d; set a [expr {$a-$nc_halo}]; set b [expr {$b-$nc_halo}]; set c [expr {$c+$nc_halo}]; set d [expr {$d+$nc_halo}]
    if {$x > $a && $x < $c && $y > $b && $y < $d} {
      lassign [lindex [lsort -real -index 0 [list [list [expr {$x-$a}] $a $y] [list [expr {$c-$x}] $c $y] [list [expr {$y-$b}] $x $b] [list [expr {$d-$y}] $x $d]]] 0] _ x y
    }
  }
  return [list $x $y]
}
set rs_keepf {}
set rs_want {}; set rs_inst {}; set rs_pins 0; set rs_seated 0; set rs_t0 0.0; set rs_slot {}; set rs_pin_of {}
foreach rs_m [$nc_blk getInsts] {
  if {![[$rs_m getMaster] isBlock]} continue
  set rs_b [$rs_m getBBox]; set ma [$rs_b xMin]; set mb [$rs_b yMin]; set mc [$rs_b xMax]; set md [$rs_b yMax]
  foreach rs_it [$rs_m getITerms] {
    if {![$rs_it isInputSignal] || [$rs_it getNet] eq "NULL" || [[$rs_it getNet] getSigType] ne "SIGNAL"} continue
    lassign [rs_cone $rs_it] rs_roots rs_gates rs_ok
    if {!$rs_ok || ![dict size $rs_roots]} continue
    set rs_all 1; dict for {nm i} $rs_roots { if {![regexp $rs_root_re [rs_name $i]]} { set rs_all 0; break } }
    if {!$rs_all} continue
    incr rs_pins
    lassign [nc_ctr $rs_it] px py
    set rs_far 0
    dict for {nm i} $rs_roots { lassign [nc_ctr $i] x y; set rs_far [expr {max($rs_far, abs($x-$px)+abs($y-$py))}] }
    set rs_t0 [expr {max($rs_t0, $rs_far/double($nc_dbu))}]
    if {$rs_far <= $rs_tail_um * $nc_dbu} {
      dict for {nm i} $rs_roots { if {[regexp {_f[./](?:r\[[0-9]+\]|q)} [rs_name $i]]} { dict set rs_keepf $nm $i } }
      continue
    }
    # the face the pin is on, and the outward unit vector
    set rs_f [lindex [lsort -index 0 -real [list [list [expr {abs($px-$ma)}] -1 0 $ma $py] [list [expr {abs($px-$mc)}] 1 0 $mc $py] [list [expr {abs($py-$mb)}] 0 -1 $px $mb] [list [expr {abs($py-$md)}] 0 1 $px $md]]] 0]
    lassign $rs_f _ ox oy ex ey
    set rs_key "[$rs_m getName] $ox $oy"; dict incr rs_slot $rs_key; set rs_k [expr {[dict get $rs_slot $rs_key] % 4}]
    set rs_dyn [rs_dynamic $rs_roots $rs_gates]
    # depth outside the halo edge (um): gates 0.3, count stages 0.9 + 0.54 k, last fixed stage 3.3 + 0.54 k
    foreach {cls dep} [list g 0.3 c [expr {0.9 + 0.54*$rs_k}] f [expr {3.3 + 0.54*$rs_k}]] {
      set rs_pt($cls) [list [expr {$ex + $ox*($nc_halo + $dep*$nc_dbu)}] [expr {$ey + $oy*($nc_halo + $dep*$nc_dbu)}]]
    }
    dict for {nm i} $rs_roots {
      if {![nc_mov $i]} continue
      set cls [expr {[regexp {_f[./](?:r\[[0-9]+\]|q)} [rs_name $i]] ? "f" : "c"}]
      dict lappend rs_want $nm $rs_pt($cls); dict set rs_inst $nm [list $i $cls]; dict set rs_pin_of $nm [list $px $py]
    }
    dict for {nm i} $rs_dyn { if {[nc_mov $i]} { dict lappend rs_want $nm $rs_pt(g); dict set rs_inst $nm [list $i g] } }
    incr rs_seated
  }
}
set rs_tgt {}; set rs_shared 0; set rs_nroot 0; set rs_ngate 0
dict for {nm pts} $rs_want {
  lassign [dict get $rs_inst $nm] i cls
  if {$cls eq "g"} { incr rs_ngate } else { incr rs_nroot; if {[llength $pts] > 1} { incr rs_shared } }
  lassign [nc_median_pt $pts] x y
  dict set rs_tgt $nm [rs_out $x $y]
}
# a last fixed stage that stays where it is (its pin is already seated) still ends a chain: spread only when a hop is long
dict for {nm i} $rs_keepf { if {![dict exists $rs_inst $nm]} { dict set rs_inst $nm [list $i k] } }
# earlier fixed stages behind each seated last-fixed flop: equal fractions of the route head -> seat
set rs_chains 0; set rs_stages 0; set rs_hop 0.0; set rs_need 0; set rs_bufs 0; set rs_noroute 0
dict for {nm v} $rs_inst {
  lassign $v rs_F cls; if {$cls ne "f" && $cls ne "k"} continue
  if {![regexp {^(.*_f)[./](?:r\[[0-9]+\]|q)} [rs_name $rs_F] _ rs_bank]} continue
  set seq {}; set hopb {}; set cur $rs_F; set head ""
  while {[llength $seq] < 64} {
    set dp [nc_dpin $cur]; if {$dp eq ""} break
    lassign [nc_back $dp] drv bufs
    lappend hopb $bufs
    if {$drv eq ""} break
    set di [$drv getInst]
    if {![[$di getMaster] isBlock] && [rs_isff $di] && [nc_mov $di] && [string first "$rs_bank" [rs_name $di]] == 0 \
        && ![dict exists $rs_inst [$di getName]] && [nc_loads $di] == 1} { set seq [linsert $seq 0 $di]; set cur $di; continue }
    set head $drv; break
  }
  if {$head eq ""} continue
  lassign [nc_ctr [expr {[[[$head getInst] getMaster] isBlock] ? $head : [$head getInst]}]] hx hy
  if {$cls eq "k"} {
    lassign [nc_ctr $rs_F] tx ty
    set prev [list $hx $hy]; set mx 0
    foreach s_ [concat $seq [list $rs_F]] { lassign [nc_ctr $s_] x y; set mx [expr {max($mx, abs($x-[lindex $prev 0])+abs($y-[lindex $prev 1]))}]; set prev [list $x $y] }
    if {$mx <= $rs_hop_thr * $nc_dbu} continue
  } else { lassign [dict get $rs_tgt $nm] tx ty }
  set route [nc_route_bit $hx $hy $tx $ty [$rs_F getName]]
  if {![nc_ok $route]} { incr rs_noroute; continue }
  set n [llength $seq]; set hops [expr {$n + 1}]
  set hop [expr {[nc_len $route]/double($hops)/$nc_dbu}]
  set rs_hop [expr {max($rs_hop, $hop)}]; if {$hop > 405.0} { incr rs_need }
  for {set j 0} {$j < $n} {incr j} {
    lassign [nc_at $route [expr {double($j+1)/$hops}]] x y
    dict set rs_tgt [[lindex $seq $j] getName] [list $x $y]; dict set rs_inst [[lindex $seq $j] getName] [list [lindex $seq $j] s]; incr rs_stages
  }
  # hop buffers: hopb[k] = buffers on the D of (F, seq[n-1], ..., seq[0]) nearest-first; the hop ends at position n+1-k
  for {set k 0} {$k < [llength $hopb] && $k <= $n} {incr k} {
    set bs [lindex $hopb $k]; set nb [llength $bs]
    for {set q 0} {$q < $nb} {incr q} {
      set bi [lindex $bs $q]; if {![nc_mov $bi] || [nc_loads $bi] != 1 || [dict exists $rs_inst [$bi getName]]} continue
      set f [expr {(($n + 1 - $k) - double($q+1)/($nb+1)) / $hops}]; if {$f < 0} { set f 0 }
      lassign [nc_at $route $f] x y
      dict set rs_tgt [$bi getName] [list $x $y]; dict set rs_inst [$bi getName] [list $bi b]; incr rs_bufs
    }
  }
  incr rs_chains
}
dict for {nm xy} $rs_tgt { lassign $xy x y; nc_put [lindex [dict get $rs_inst $nm] 0] $x $y }
set rs_kept [dict size $rs_keepf]
set rs_t1 0.0
dict for {nm pxy} $rs_pin_of { lassign $pxy px py; lassign [nc_ctr [lindex [dict get $rs_inst $nm] 0]] x y; set rs_t1 [expr {max($rs_t1, (abs($x-$px)+abs($y-$py))/double($nc_dbu))}] }
puts [format "OT_R8_CORE_SEAT pins %d seated_pins %d roots %d shared_roots %d gates %d chains %d stages_moved %d hop_bufs_moved %d noroute %d tail_um max before %.1f after %.1f chain_hop_um max %.1f need_stage %d kept_tails %d" \
  $rs_pins $rs_seated $rs_nroot $rs_shared $rs_ngate $rs_chains $rs_stages $rs_bufs $rs_noroute $rs_t0 $rs_t1 $rs_hop $rs_need $rs_kept]
}
}
uplevel #0 { puts "OT_NK_CHAIN_LANE on $nc_lane_on buses [dict size $nc_lane_w] laned_routes $nc_lane_used fallback_centre $nc_lane_fallback" }
# lever 7 (HOLD-FLOW-R 11-17): this kit's PRE_RESIZE hook is this file, not the gp_noconverge gate: run the post-place wire check here
if {[file exists [file join [file dirname [file normalize [info script]]] place_wire_ratio.tcl]]} { source [file join [file dirname [file normalize [info script]]] place_wire_ratio.tcl] }
