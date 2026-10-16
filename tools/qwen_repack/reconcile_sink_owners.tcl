# Reconcile repair cells with actual exclusive sink ownership before ordinary DPL.
# No cells, nets, FFs, clock checks or timing constraints are added/removed.
namespace eval q4r {}
proc q4r::lower {rows y} {
 set lo 0;set hi [llength $rows]
 while {$lo<$hi} {set mid [expr {($lo+$hi)/2}];if {[lindex $rows $mid 0]<$y} {set lo [expr {$mid+1}]} else {set hi $mid}}
 return $lo
}
proc q4r::cut {intervals lo hi} {
 set out {}
 foreach interval $intervals {lassign $interval a b
  if {$hi<=$a || $lo>=$b} {lappend out $interval;continue}
  if {$a<$lo} {lappend out [list $a $lo]};if {$hi<$b} {lappend out [list $hi $b]}
 }
 return $out
}
# Merge occupancy once per row instead of repeatedly splitting its interval list
# for every mapped cell; this keeps large repair populations linear after sort.
proc q4r::subtract_sorted {intervals cuts} {
 set merged {}
 foreach cut [lsort -integer -index 0 $cuts] {
  lassign $cut a b
  if {![llength $merged] || $a>[lindex $merged end 1]} {lappend merged $cut
  } else {lset merged end 1 [expr {max($b,[lindex $merged end 1])}]}
 }
 set out {};set idx 0;set n [llength $merged]
 foreach interval $intervals {
  lassign $interval a b
  while {$idx<$n && [lindex $merged $idx 1]<=$a} {incr idx}
  set cursor $a;set j $idx
  while {$j<$n && [lindex $merged $j 0]<$b} {
   lassign [lindex $merged $j] lo hi
   if {$lo>$cursor} {lappend out [list $cursor [expr {min($lo,$b)}]]}
   set cursor [expr {max($cursor,min($hi,$b))}]
   if {$cursor>=$b} break
   incr j
  }
  if {$cursor<$b} {lappend out [list $cursor $b]}
 };return $out
}
proc q4r::intersect {intervals lo hi} {
 set out {};foreach interval $intervals {lassign $interval a b
  set a [expr {max($a,$lo)}];set b [expr {min($b,$hi)}];if {$a<$b} {lappend out [list $a $b]}
 };return $out
}
proc q4r::root {net {depth 0}} {
 variable root_cache
 if {$depth>60} {error "Q4R clock trace exceeded60"}
 if {[dict exists $root_cache [$net getId]]} {return [dict get $root_cache [$net getId]]}
 foreach bt [$net getBTerms] {if {[$bt getIoType] eq "INPUT"} {dict set root_cache [$net getId] [$bt getName];return [$bt getName]}}
 foreach it [$net getITerms] {if {![$it isOutputSignal]} continue
  set i [$it getInst]
  if {![regexp {^(BUF|INV|CLK)} [[$i getMaster] getName]]} {error "Q4R unexpected clock driver [$i getName]"}
  foreach p [$i getITerms] {if {[$p isInputSignal] && [$p getNet] ne "NULL"} {
   set r [q4r::root [$p getNet] [expr {$depth+1}]];dict set root_cache [$net getId] $r;return $r
  }}
 };error "Q4R undriven clock [$net getName]"
}
proc q4r::cone {queue} {
 set seen [dict create];set cells [dict create];set launch [dict create]
 while {[llength $queue]} {
  set n [lindex $queue end];set queue [lrange $queue 0 end-1]
  if {[dict exists $seen [$n getId]]} continue
  dict set seen [$n getId] 1
  foreach it [$n getITerms] {if {![$it isOutputSignal]} continue
   set i [$it getInst];set m [$i getMaster]
   if {[$m isBlock]} {dict set launch HARD:[$i getName] 1;continue}
   if {[$m isSequential]} {
    set cp [$i findITerm CLK]
    if {$cp eq "NULL" || [$cp getNet] eq "NULL"} {error "Q4R sequential clock missing"}
    dict set launch [q4r::root [$cp getNet]] 1;continue
   }
   if {[dict exists $cells [$i getName]]} continue
   dict set cells [$i getName] $i
   foreach p [$i getITerms] {if {[$p isInputSignal] && [$p getNet] ne "NULL"} {lappend queue [$p getNet]}}
  }
 };return [list $cells [dict keys $launch]]
}
proc q4r::rect {i} {set b [$i getBBox];return [list [$b xMin] [$b yMin] [$b xMax] [$b yMax]]}
proc q4r::inside {rect boxes} {
 lassign $rect x y u v
 foreach box $boxes {lassign $box a b c d;if {$x>=$a && $y>=$b && $u<=$c && $v<=$d} {return 1}}
 return 0
}
proc q4r::overlap {rect boxes} {
 lassign $rect x y u v
 foreach box $boxes {lassign $box a b c d;if {$x<$c && $u>$a && $y<$d && $v>$b} {return 1}}
 return 0
}
proc q4r::gap {rect boxes} {
 # Manhattan distance (dbu) from a cell rectangle to the nearest fence box (0 when it overlaps one)
 lassign $rect x y u v;set best Inf
 foreach box $boxes {lassign $box a b c d
  set dx [expr {$u<$a ? $a-$u : ($x>$c ? $x-$c : 0)}];set dy [expr {$v<$b ? $b-$v : ($y>$d ? $y-$d : 0)}]
  set best [expr {min($best,$dx+$dy)}]
 };return $best
}
proc q4r::subtract {rows free_name rect maxheight} {
 upvar 1 $free_name free
 lassign $rect x0 y0 x1 y1
 set ri [q4r::lower $rows [expr {$y0-$maxheight}]]
 for {} {$ri<[llength $rows]} {incr ri} {
  lassign [lindex $rows $ri] y x ex ey pitch orient
  if {$y >= $y1} break
  if {$ey > $y0} {dict set free $ri [q4r::cut [dict get $free $ri] $x0 $x1]}
 }
}
proc q4r::allowed {row intervals boxes outside} {
 lassign $row y x ex ey pitch orient
 if {$outside} {
  foreach box $boxes {lassign $box a b c d;if {$y<$d && $ey>$b} {set intervals [q4r::cut $intervals $a $c]}}
  return $intervals
 }
 set out {}
 foreach box $boxes {lassign $box a b c d
  if {$y>=$b && $ey<=$d} {lappend out {*}[q4r::intersect $intervals $a $c]}
 };return $out
}
proc q4r::run {} {
 variable root_cache;set root_cache [dict create]
 set block [ord::get_db_block];set dbu [$block getDbUnitsPerMicron]
 set counts [list [llength [$block getInsts]] [llength [$block getNets]]]
 set regs [dict create];set owners [dict create];set cells [dict create]
 foreach i [$block getInsts] {
  set m [$i getMaster];if {[$m isBlock] || ![$m isSequential]} continue
  set cp [$i findITerm CLK]
  if {$cp eq "NULL" || [$cp getNet] eq "NULL"} {error "Q4R sequential clock missing [$i getName]"}
  dict lappend regs [q4r::root [$cp getNet]] $i
 }
 dict for {root is} $regs {
  set queue {}
  foreach i $is {foreach it [$i getITerms] {
   if {[$it isInputSignal] && [[$it getMTerm] getName] ne "CLK" && [$it getNet] ne "NULL"} {lappend queue [$it getNet]}
  }}
  lassign [q4r::cone $queue] cs ignored
  dict for {name i} $cs {dict lappend owners $name $root;dict set cells $name $i}
 }
 foreach bt [$block getBTerms] {
  if {[$bt getIoType] ne "OUTPUT" || [$bt getSigType] in {POWER GROUND} || [$bt getNet] eq "NULL"} continue
  lassign [q4r::cone [list [$bt getNet]]] cs roots
  dict for {name i} $cs {foreach root $roots {dict lappend owners $name $root};dict set cells $name $i}
 }
 set boxes [dict create];set allboxes {};set groups [dict create]
 foreach g [$block getGroups] {
  if {![string match q45_* [$g getName]]} continue
  set r [$g getRegion];if {$r eq "NULL"} continue
  set bs {};foreach b [$r getBoundaries] {lappend bs [list [$b xMin] [$b yMin] [$b xMax] [$b yMax]]}
  dict set boxes [$g getName] $bs;dict set groups [$g getName] $g;lappend allboxes {*}$bs
 }
 if {![dict size $groups]} {error "Q4R no actual q45 sink groups"}
 set attached [dict create];set shared 0;set seed [dict create];set legcells [dict create]
 set leg [expr {round(([info exists ::env(Q4R_LEG_UM)] ? $::env(Q4R_LEG_UM) : 20.0)*$dbu)}]
 dict for {name roots} $owners {
  set roots [lsort -unique $roots];if {[llength $roots]!=1} {incr shared;continue}
  set gn q45_[lindex $roots 0]
  if {![dict exists $groups $gn]} continue
  set i [dict get $cells $name]
  if {[$i getGroup] ne "NULL"} continue
  # Q-TILE45c 2026-10-16: a repeater placed on an inbound leg (> leg_um outside its owner's fence) serves the leg, not
  # the sink cluster; pulling it into the fence collapses the leg (NK g4u 3_4: 10,628 of 13,100 ck_rs cone cells, 2,067
  # of 2,245 um2, sat a mean 123 um away -> Q4R ck_rs fill 0.61).  It stays ungrouped on its leg (seeded OUTSIDE only
  # if it overlaps an exclusive fence).
  if {[regexp {^(BUF|INV|HB)} [[$i getMaster] getName]] && [q4r::gap [q4r::rect $i] [dict get $boxes $gn]] > $leg} {dict incr legcells $gn;continue}
  if {[$i getPlacementStatus] in {FIRM LOCKED COVER}} {error "Q4R refuses to regroup a fixed repair cell $name"}
  [dict get $groups $gn] addInst $i;dict incr attached $gn
  if {![q4r::inside [q4r::rect $i] [dict get $boxes $gn]]} {dict set seed $name [list $i $gn]}
 }
 # Shared/unfenced repair cells cannot legally remain inside somebody else's EXCLUSIVE fence.
 foreach i [$block getInsts] {
  set m [$i getMaster]
  if {[$m isBlock] || [$i getPlacementStatus] in {FIRM LOCKED COVER} || [$i getGroup] ne "NULL"} continue
  if {![q4r::overlap [q4r::rect $i] $allboxes]} continue
  if {[$m isSequential]} {error "Q4R unowned sequential sink intersects an exclusive fence [$i getName]"}
  dict set seed [$i getName] [list $i OUTSIDE]
 }
 set rows {};set maxheight 0
 foreach row [$block getRows] {
  set b [$row getBBox];set h [expr {[$b yMax]-[$b yMin]}];set pitch [$row getSpacing]
  if {$h<=0 || $pitch<=0} continue
  if {$pitch != [[$row getSite] getWidth]} {error "Q4R sparse row sites unsupported"}
  lappend rows [list [$b yMin] [$b xMin] [$b xMax] [$b yMax] $pitch [$row getOrient]]
  set maxheight [expr {max($maxheight,$h)}]
 }
 set rows [lsort -integer -index 0 $rows]
 if {![llength $rows]} {error "Q4R no actual rows"}
 set fixedfree [dict create];set ri 0
 foreach row $rows {dict set fixedfree $ri [list [list [lindex $row 1] [lindex $row 2]]];incr ri}
 foreach i [$block getInsts] {if {[$i getPlacementStatus] in {FIRM LOCKED COVER}} {q4r::subtract $rows fixedfree [q4r::rect $i] $maxheight}}
 foreach b [$block getBlockages] {set r [$b getBBox];q4r::subtract $rows fixedfree [list [$r xMin] [$r yMin] [$r xMax] [$r yMax]] $maxheight}
 dict for {gn bs} $boxes {
  set capacity 0;set ri 0
  foreach row $rows {
   lassign $row y x ex ey pitch orient
   foreach interval [q4r::allowed $row [dict get $fixedfree $ri] $bs 0] {
    lassign $interval a b
    set lo [expr {$x+int(ceil(double($a-$x)/$pitch))*$pitch}]
    set hi [expr {$x+int(floor(double($b-$x)/$pitch))*$pitch}]
    if {$hi>$lo} {set capacity [expr {$capacity+double($hi-$lo)*($ey-$y)/$dbu/$dbu}]}
   };incr ri
  }
  set area 0
  foreach i [[dict get $groups $gn] getInsts] {
   if {[$i getPlacementStatus] in {FIRM LOCKED COVER}} {error "Q4R capacity requires released group cells [$i getName]"}
   set m [$i getMaster];set area [expr {$area+double([$m getWidth])*[$m getHeight]/$dbu/$dbu}]
  }
  if {$capacity<=0 || $area>.60*$capacity} {error "Q4R actual row capacity FAIL $gn area=$area capacity=$capacity"}
  puts "Q4R_ACTUAL_CAPACITY $gn area=$area capacity=$capacity fill=[expr {$area/$capacity}]"
 }
 set cuts [dict create]
 foreach i [$block getInsts] {
  if {[$i getPlacementStatus] in {FIRM LOCKED COVER} || [dict exists $seed [$i getName]]} continue
  lassign [q4r::rect $i] x0 y0 x1 y1
  set ri [q4r::lower $rows [expr {$y0-$maxheight}]]
  for {} {$ri<[llength $rows]} {incr ri} {
   lassign [lindex $rows $ri] y x ex ey pitch orient
   if {$y>=$y1} break
   if {$ey>$y0} {dict lappend cuts $ri [list $x0 $x1]}
  }
 }
 set free $fixedfree
 dict for {ri intervals} $cuts {dict set free $ri [q4r::subtract_sorted [dict get $fixedfree $ri] $intervals]}
 puts "Q4R_SEED_BEGIN selected=[dict size $seed] attached=$attached shared=$shared leg_repeaters_left_on_leg=$legcells"
 set report [expr {[info exists ::env(Q4R_REPORT)] ? $::env(Q4R_REPORT) : "q4_reconcile_seeds.tsv"}]
 set f [open $report w];puts $f "name\towner\told_x\told_y\tnew_x\tnew_y\tmove_um"
 set maximum 0
 dict for {name item} $seed {
  lassign $item i gn;set m [$i getMaster];set w [$m getWidth];set h [$m getHeight]
  lassign [$i getLocation] ox oy;set best {};set score Inf;set ri 0
  set allowed [expr {$gn eq "OUTSIDE" ? $allboxes : [dict get $boxes $gn]}]
  set right [q4r::lower $rows $oy];set left [expr {$right-1}]
  while {$left>=0 || $right<[llength $rows]} {
   set lc Inf;set rc Inf
   if {$left>=0} {set lc [expr {abs([lindex $rows $left 0]-$oy)}]}
   if {$right<[llength $rows]} {set rc [expr {abs([lindex $rows $right 0]-$oy)}]}
   if {min($lc,$rc)>$score} break
   if {$lc<=$rc} {set ri $left;incr left -1} else {set ri $right;incr right}
   set row [lindex $rows $ri];lassign $row y x ex ey pitch orient
   if {$ey-$y != $h} continue
   foreach interval [q4r::allowed $row [dict get $free $ri] $allowed [expr {$gn eq "OUTSIDE"}]] {
    lassign $interval a b
    set lo [expr {$x+int(ceil(double($a-$x)/$pitch))*$pitch}]
    set hi [expr {$x+int(floor(double($b-$w-$x)/$pitch))*$pitch}]
    if {$hi<$lo} continue
    set px [expr {max($lo,min($hi,$x+round(double($ox-$x)/$pitch)*$pitch))}]
    set d [expr {abs($px-$ox)+abs($y-$oy)}]
    if {$d<$score} {set score $d;set best [list $ri $px $y $orient]}
   }
  }
  if {$best eq ""} {error "Q4R no actual free row site for $name owner=$gn"}
  lassign $best ri x y orient
  $i setOrient $orient;$i setLocation $x $y
  dict set free $ri [q4r::cut [dict get $free $ri] $x [expr {$x+$w}]]
  set maximum [expr {max($maximum,double($score)/$dbu)}]
  puts $f "$name\t$gn\t$ox\t$oy\t$x\t$y\t[expr {double($score)/$dbu}]"
 }
 close $f
 if {$counts ne [list [llength [$block getInsts]] [llength [$block getNets]]]} {error "Q4R changed cell/net counts"}
 puts "Q4R_RECONCILE_PASS attached=$attached shared=$shared seeded=[dict size $seed] max_move_um=$maximum unchanged_cells_nets=$counts"
}
q4r::run
