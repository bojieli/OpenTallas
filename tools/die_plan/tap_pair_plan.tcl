# Pure planner for default-off short-pair clock affinity.  Rows are
# instance -> {clock_iterm x_dbu y_dbu tap}; iterms are opaque to the planner.
# Initial same-tap short-pair components are indivisible.  A move can remove
# a boundary, but cannot introduce one inside an initially coherent component.
namespace eval ::ot_tap_pair {
 proc root {parent_var name} {
  upvar 1 $parent_var parent
  set r $name
  while {[dict get $parent $r] ne $r} {set r [dict get $parent $r]}
  while {[dict get $parent $name] ne $name} {
   set next [dict get $parent $name];dict set parent $name $r;set name $next
  }
  return $r
 }
 proc cand_cmp {a b} {
  # merge candidates {members_on_tap sum_dist tap}: most members, then nearest, then name
  if {[lindex $a 0]!=[lindex $b 0]} {return [expr {[lindex $a 0]>[lindex $b 0] ? -1 : 1}]}
  if {[lindex $a 1]!=[lindex $b 1]} {return [expr {[lindex $a 1]<[lindex $b 1] ? -1 : 1}]}
  return [string compare [lindex $a 2] [lindex $b 2]]
 }
 proc plan {regs pairs tapxy load cap radius limit maxpasses {mergelimit 0} {shift 0} {grow 0}} {
  if {$cap<1 || $radius<=0 || $limit<2 || $limit>$cap || $maxpasses<1} {
   error "OT_TAP_PAIR invalid capacity/radius/group/passes"
  }
  if {![string is double -strict $grow] || $grow<0 || $grow>0.5} {error "OT_TAP_PAIR invalid overfull growth $grow"}
  # DIE-QC-97 11-09: the initial load must be KNOWN for every tap, but it may exceed cap.  clock_taps.tcl keeps an
  # over-full tap with no room within the reassign radius as a WARN (COORD 10-23 19:55: sinks per tap are guidance,
  # not a gate) and leaves hard-core clock pins on their tap, so taps above cap are legal inputs (QC cbn_q00 clk_t11,
  # slw_su_c: CTS stopped here).  Every move below admits a tap only while load+n<=cap, so an over-full tap only
  # donates; the end check proves no tap is left above max(cap, its initial load).
  set initload {}
  dict for {tap xy} $tapxy {
   if {![dict exists $load $tap] || ![string is integer -strict [dict get $load $tap]] || [dict get $load $tap]<0} {
    error "OT_TAP_PAIR initial tap capacity invalid: $tap"
   }
   dict set initload $tap [dict get $load $tap]
  }
  # DIE-QC-97 11-10 OVERFULL ADMISSION (grow>0, plan clock.tap_pair_affinity.overfull_grow): a tap may receive while
  # load+n <= l0 + floor(l0*grow) when it started above cap (else cap).  grow 0 = the donate-only rule above.  QC sle_hc0 (density mode, 77k sinks
  # on 15 taps, 8 above cap 1200 at start): donate-only moved 19 of the pins behind 6486 cross-tap short pairs, because
  # every pair on a boundary between two over-full taps had no admissible side; the FF hold miss there is the 40-ps
  # tap window plus the tree mismatch (p_ib -> r_ib 15 um apart, clk_t1 -> clk_t2, -100.65 ps).  The bounded growth
  # (<= grow of the tap's own size; tree depth is log of sinks) lets those components join one tap.
  set lim {}
  dict for {tap l0} $initload {dict set lim $tap [expr {$l0>$cap ? $l0 + int(floor($l0*$grow)) : $cap}]}
  set overfull [llength [lmap {tap l0} $initload {expr {$l0>$cap ? $tap : [continue]}}]]
  set parent {};set adj {}
  dict for {name row} $regs {
   if {![dict exists $tapxy [lindex $row 3]]} {error "OT_TAP_PAIR unknown source tap"}
   dict set parent $name $name
  }
  foreach edge $pairs {
   lassign $edge distance a b
   if {![dict exists $regs $a] || ![dict exists $regs $b]} {error "OT_TAP_PAIR unknown pair member"}
   if {$a eq $b} continue
   dict lappend adj $a $b;dict lappend adj $b $a
   if {[lindex [dict get $regs $a] 3] eq [lindex [dict get $regs $b] 3]} {
    set ar [root parent $a];set br [root parent $b]
    if {$ar ne $br} {
     if {[string compare $ar $br]<0} {dict set parent $br $ar} else {dict set parent $ar $br}
    }
   }
  }
  set groups {};set owner {};set largest 0;set frozen 0
  dict for {name row} $regs {
   set r [root parent $name];dict lappend groups $r $name;dict set owner $name $r
  }
  dict for {r members} $groups {
   set n [llength $members];set largest [expr {max($largest,$n)}]
   if {$n>$limit} {incr frozen}
  }
  set initial $regs;set moves 0;set groupmoves 0;set passes {};set converged 0
  for {set pass 1} {$pass<=$maxpasses} {incr pass} {
   set pm 0;set gm 0
   dict for {r members} $groups {
    set n [llength $members]
    if {$n>$limit} continue
    set old [lindex [dict get $regs [lindex $members 0]] 3]
    set votes {}
    foreach v $members {
     if {[lindex [dict get $regs $v] 3] ne $old} {error "OT_TAP_PAIR coherent component split"}
     if {![dict exists $adj $v]} continue
     foreach u [dict get $adj $v] {
      if {[dict get $owner $u] eq $r} continue
      dict incr votes [lindex [dict get $regs $u] 3]
     }
    }
    set current [expr {[dict exists $votes $old] ? [dict get $votes $old] : 0}]
    set best {};set score $current;set cost 0
    dict for {tap count} $votes {
     if {$tap eq $old || $count<=$current || $count<$score || [dict get $load $tap]+$n>[dict get $lim $tap]} continue
     lassign [dict get $tapxy $tap] tx ty
     set sum 0;set good 1
     foreach v $members {
      lassign [dict get $regs $v] it x y t
      set d [expr {abs($x-$tx)+abs($y-$ty)}]
      if {$d>$radius} {set good 0;break}
      set sum [expr {$sum+$d}]
     }
     if {!$good} continue
     if {$best eq {} || $count>$score || ($count==$score && $sum<$cost)} {
      set best $tap;set score $count;set cost $sum
     }
    }
    if {$best eq {}} continue
    foreach v $members {
     set row [dict get $regs $v];lset row 3 $best;dict set regs $v $row
    }
    dict incr load $old -$n;dict incr load $best $n
    incr pm $n;incr gm
   }
   set cross 0
   foreach edge $pairs {
    lassign $edge distance a b
    if {[lindex [dict get $regs $a] 3] ne [lindex [dict get $regs $b] 3]} {incr cross}
   }
   lappend passes [list $pass $gm $pm $cross]
   incr moves $pm;incr groupmoves $gm
   if {!$pm} {set converged 1;break}
  }
  # QC-TYPES-6 v2 MERGE phase (mergelimit > 1): label propagation stalls on vote ties, e.g. a ring
  # delay chain bin -> pd5 r0..r3 -> q -> xh2 capture whose bits alternate taps (vPAC: 149 of the 161
  # reg-to-reg FF hold paths under -40 ps).  A whole connected component of the pair graph (all pairs,
  # not only same-tap ones) with at most mergelimit registers moves onto one tap: the tap holding most
  # of its members, then the smallest summed distance, within radius and tap capacity.  It has no pair
  # leaving it, so the move cannot cut any pair, coherent or not.
  set merged 0;set mergemoves 0
  if {$mergelimit>1} {
   set fp {}
   dict for {name row} $regs {dict set fp $name $name}
   foreach edge $pairs {
    lassign $edge distance a b
    if {$a eq $b} continue
    set ar [root fp $a];set br [root fp $b]
    if {$ar ne $br} {
     if {[string compare $ar $br]<0} {dict set fp $br $ar} else {dict set fp $ar $br}
    }
   }
   set full {}
   dict for {name row} $regs {dict lappend full [root fp $name] $name}
   set hot {}
   foreach edge $pairs {
    lassign $edge distance a b
    if {[lindex [dict get $regs $a] 3] ne [lindex [dict get $regs $b] 3]} {dict set hot [root fp $a] 1}
   }
   foreach r [lsort [dict keys $hot]] {
    set members [dict get $full $r];set n [llength $members]
    if {$n>$mergelimit} continue
    set cnt {}
    foreach v $members {dict incr cnt [lindex [dict get $regs $v] 3]}
    set cands {}
    dict for {tap c} $cnt {
     lassign [dict get $tapxy $tap] tx ty
     set sum 0;set good 1
     foreach v $members {
      lassign [dict get $regs $v] it x y t
      set d [expr {abs($x-$tx)+abs($y-$ty)}]
      if {$d>$radius} {set good 0;break}
      set sum [expr {$sum+$d}]
     }
     if {!$good || [dict get $load $tap]+$n-$c>[dict get $lim $tap]} continue
     lappend cands [list $c $sum $tap]
    }
    if {![llength $cands]} continue
    set best [lindex [lsort -command ::ot_tap_pair::cand_cmp $cands] 0 2]
    foreach v $members {
     set row [dict get $regs $v];set old [lindex $row 3]
     if {$old eq $best} continue
     lset row 3 $best;dict set regs $v $row
     dict incr load $old -1;dict incr load $best 1;incr mergemoves
    }
    incr merged
   }
   set cross 0
   foreach edge $pairs {
    lassign $edge distance a b
    if {[lindex [dict get $regs $a] 3] ne [lindex [dict get $regs $b] 3]} {incr cross}
   }
   lappend passes [list merge $merged $mergemoves $cross]
   incr moves $mergemoves
  }
  # QC-TYPES-6 v4 SHIFT phase (shift>0, after merge): where a cut must stay (a chain inside a component too large to
  # merge), put it on the LONGEST pair: a phase-1 group moves to a tap with exactly as many votes as its own (same
  # cross count) only if the summed distance of its cross pairs grows, so the unavoidable tap boundary lands where
  # the data path has the most wire to absorb the tap skew (vPAC3: xh2 lw_ctl[106] -> xl2_4 wctl[34], 2.7 um
  # apart, -65.12 ps).  The total cross distance rises strictly, so the passes converge.
  set shifts 0
  if {$shift>0} {
   set dist {}
   foreach edge $pairs {
    lassign $edge distance a b
    if {$a eq $b} continue
    dict lappend dist $a [list $b $distance];dict lappend dist $b [list $a $distance]
   }
   for {set sp 0} {$sp<$shift} {incr sp} {
    set sm 0
    dict for {r members} $groups {
     set n [llength $members]
     if {$n>$limit} continue
     set old [lindex [dict get $regs [lindex $members 0]] 3]
     set votes {};set ext {}
     foreach v $members {
      if {![dict exists $dist $v]} continue
      foreach ud [dict get $dist $v] {
       lassign $ud u d
       if {[dict get $owner $u] eq $r} continue
       set t [lindex [dict get $regs $u] 3]
       dict incr votes $t;lappend ext [list $t $d]
      }
     }
     set current [expr {[dict exists $votes $old] ? [dict get $votes $old] : 0}]
     set s0 0;foreach e $ext {if {[lindex $e 0] ne $old} {set s0 [expr {$s0+[lindex $e 1]}]}}
     set best {};set bs $s0
     dict for {tap count} $votes {
      if {$tap eq $old || $count!=$current || [dict get $load $tap]+$n>[dict get $lim $tap]} continue
      set s 0;foreach e $ext {if {[lindex $e 0] ne $tap} {set s [expr {$s+[lindex $e 1]}]}}
      if {$s<=$bs} continue
      lassign [dict get $tapxy $tap] tx ty;set good 1
      foreach v $members {
       lassign [dict get $regs $v] it x y t
       if {abs($x-$tx)+abs($y-$ty)>$radius} {set good 0;break}
      }
      if {$good} {set best $tap;set bs $s}
     }
     if {$best eq {}} continue
     foreach v $members {set row [dict get $regs $v];lset row 3 $best;dict set regs $v $row}
     dict incr load $old -$n;dict incr load $best $n;incr sm
    }
    incr shifts $sm
    if {!$sm} break
   }
   set cross 0
   foreach edge $pairs {
    lassign $edge distance a b
    if {[lindex [dict get $regs $a] 3] ne [lindex [dict get $regs $b] 3]} {incr cross}
   }
   lappend passes [list shift $shifts $shifts $cross]
  }
  # Fail before any physical connection changes if a promised invariant is lost.
  dict for {tap l0} $initload {
   if {[dict get $load $tap]>[dict get $lim $tap]} {error "OT_TAP_PAIR tap filled above capacity: $tap"}
  }
  foreach edge $pairs {
   lassign $edge distance a b
   if {[lindex [dict get $initial $a] 3] eq [lindex [dict get $initial $b] 3] &&
       [lindex [dict get $regs $a] 3] ne [lindex [dict get $regs $b] 3]} {
    error "OT_TAP_PAIR introduced an initial coherent-pair cut"
   }
  }
  return [dict create regs $regs load $load passes $passes moves $moves groupmoves $groupmoves \
   components [dict size $groups] largest $largest frozen $frozen converged $converged overfull $overfull]
 }
}
