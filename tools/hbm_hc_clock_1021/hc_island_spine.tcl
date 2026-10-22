# HBM-ELEM13/HC 10-21: generic SRAM-island-aware symmetric clock spine for the
# HC ring banks (E2/B0/CB). Cause (E2 baseline replay 3b4b14119 + B0 per-pin
# 147729d92): a glue root whose real CLK sinks sit on BOTH sides of an SRAM
# column gets (a) one bbox split across the column with collapse-unequal depth
# and (b) a fork at the face root pin, so the far island's trunk carries extra
# path repeaters (ot_sp_path every OT_SPINE_SEG) -> 70-140 ps inter-island skew.
# Fix: one local subtree per physical island (x-intervals between SRAM column
# edges), equal buffer depth, and (fork=mid) a fork placed OUTSIDE every macro
# at the x-midpoint of the island subtree roots, so both trunks have the same
# length and the same number of path repeaters. Same root/clock/edges, no dummy
# loads, no registers, no SDC/RC/Lib change.
# Config (set by the kit before sourcing):
#   ::ot_hci_roots  roots to rebuild; others keep the previous build
#   ::ot_hci_skip   roots always delegated (already actual-validated builds)
#   ::ot_hci_fork   mid | root
#   ::ot_hci_tag    log tag
if {[info procs ot_sp_sym_build] eq "" || [info procs ot_hci_prev_build] ne ""} {
  error "HC_ISLAND: expected one fresh symmetric spine build"
}
foreach v {ot_hci_roots ot_hci_fork} {
  if {![info exists ::$v]} {error "HC_ISLAND: ::$v not set by the kit"}
}
if {![info exists ::ot_hci_skip]} {set ::ot_hci_skip {}}
if {![info exists ::ot_hci_tag]} {set ::ot_hci_tag HC_ISLAND}
#   ::ot_hci_multi_only 1 -> roots whose sinks sit in ONE island keep the previous build
if {![info exists ::ot_hci_multi_only]} {set ::ot_hci_multi_only 0}
rename ot_sp_sym_build ot_hci_prev_build

proc ot_hci_unary {child} {
  set n "N[incr ::ot_sp_nn]"
  dict set ::ot_sp_pos $n [dict get $::ot_sp_pos $child]
  dict set ::ot_sp_cnt $n [dict get $::ot_sp_cnt $child]
  dict set ::ot_sp_kids $n [list $child]
  return $n
}
proc ot_hci_depth {n} {
  if {![dict exists $::ot_sp_kids $n]} {return 0}
  set heights {};set high 0;set kids [dict get $::ot_sp_kids $n]
  foreach k $kids {set h [ot_hci_depth $k];lappend heights $h;set high [expr {max($high,$h)}]}
  set out {}
  foreach k $kids h $heights {
    for {set i $h} {$i<$high} {incr i} {set k [ot_hci_unary $k]}
    lappend out $k
  }
  dict set ::ot_sp_kids $n $out
  return [expr {$high+1}]
}
# SRAM macro boxes (dbu) and merged column x-intervals
proc ot_hci_macros {} {
  set boxes {}
  foreach inst [$::ot_sp_blk getInsts] {
    set m [$inst getMaster]
    if {![$m isBlock] || ![string match ot_sram* [$m getName]]} continue
    set b [$inst getBBox]
    lappend boxes [list [$b xMin] [$b yMin] [$b xMax] [$b yMax]]
  }
  return $boxes
}
proc ot_hci_columns {boxes} {
  set iv [lsort -integer -index 0 [lmap b $boxes {list [lindex $b 0] [lindex $b 2]}]]
  set cols {}
  foreach i $iv {
    lassign $i a b
    if {[llength $cols] && $a <= [lindex $cols end 1]} {
      lset cols end 1 [expr {max([lindex $cols end 1],$b)}]
    } else {lappend cols [list $a $b]}
  }
  return $cols
}
proc ot_hci_island {x cols} {
  set k 0
  foreach c $cols {
    lassign $c a b
    if {$x < $a} {return "g$k"}
    if {$x <= $b} {return "c$k"}
    incr k
  }
  return "g$k"
}
proc ot_hci_inside {x y boxes} {
  foreach b $boxes {
    lassign $b x0 y0 x1 y1
    if {$x>=$x0 && $x<=$x1 && $y>=$y0 && $y<=$y1} {return 1}
  }
  return 0
}
proc ot_sp_sym_build {ids lins rx ry} {
  set port [uplevel 1 {set port}]
  if {$port ni $::ot_hci_roots || $port in $::ot_hci_skip} {
    return [ot_hci_prev_build $ids $lins $rx $ry]
  }
  if {[dict size $lins]} {
    puts "$::ot_hci_tag skip=$port hard_insertion_leaves=[dict size $lins] (previous build)"
    return [ot_hci_prev_build $ids $lins $rx $ry]
  }
  set u $::ot_sp_dbu
  set boxes [ot_hci_macros];set cols [ot_hci_columns $boxes]
  set groups [dict create];set counts [dict create]
  foreach id $ids {
    set side ""
    foreach pin [dict get $::ot_sp_members $id] {
      if {[[[$pin getInst] getMaster] isBlock]} {error "$::ot_hci_tag: hard sink on glue root $port"}
      lassign [$pin getAvgXY] ok x y
      if {!$ok} {error "$::ot_hci_tag: real pin shape absent"}
      set s [ot_hci_island $x $cols]
      if {$side ne "" && $s ne $side} {
        puts "$::ot_hci_tag skip=$port leaf $id straddles islands $side/$s (previous build)"
        return [ot_hci_prev_build $ids $lins $rx $ry]
      }
      set side $s;dict incr counts $s
    }
    dict lappend groups $side $id
  }
  if {$::ot_hci_multi_only && [dict size $groups] < 2} {
    puts "$::ot_hci_tag keep=$port single_island=$counts (previous build)"
    return [ot_hci_prev_build $ids $lins $rx $ry]
  }
  set trees {};set heights {};set height 0;set sx {};set sy {}
  foreach name [lsort [dict keys $groups]] {
    set t [ot_sp_split_bb [dict get $groups $name]]
    set h [ot_hci_depth $t];lappend trees $t;lappend heights $h
    set height [expr {max($height,$h)}]
    lassign [dict get $::ot_sp_pos $t] x y;lappend sx $x;lappend sy $y
  }
  set balanced {}
  foreach t $trees h $heights {
    for {set i $h} {$i<$height} {incr i} {set t [ot_hci_unary $t]}
    lappend balanced $t
  }
  set total 0;dict for {k v} $counts {incr total $v}
  set top "N[incr ::ot_sp_nn]"
  dict set ::ot_sp_pos $top [list $rx $ry]
  dict set ::ot_sp_cnt $top $total
  set forkxy root
  if {$::ot_hci_fork eq "mid" && [llength $balanced] > 1} {
    set fx [expr {int(([tcl::mathfunc::min {*}$sx]+[tcl::mathfunc::max {*}$sx])/2)}]
    set ty [expr {int(([tcl::mathfunc::min {*}$sy]+[tcl::mathfunc::max {*}$sy])/2)}]
    set fy $ty
    for {set d 0} {$d <= 400} {incr d} {
      set hit 0
      foreach c [list [expr {$ty+$d*$u}] [expr {$ty-$d*$u}]] {
        if {![ot_hci_inside $fx $c $boxes] && ![ot_hci_inside [expr {$fx+$::ot_sp_cw}] [expr {$c+$::ot_sp_rh}] $boxes]} {
          set fy $c;set hit 1;break
        }
      }
      if {$hit} break
    }
    set f "N[incr ::ot_sp_nn]"
    dict set ::ot_sp_pos $f [ot_sp_free $fx $fy]
    dict set ::ot_sp_cnt $f $total
    dict set ::ot_sp_kids $f $balanced
    dict set ::ot_sp_kids $top [list $f]
    set forkxy "[expr {$fx/double($u)}],[expr {$fy/double($u)}]"
  } else {
    dict set ::ot_sp_kids $top $balanced
  }
  set ::ot_sp_est_t [dict create]
  ot_sp_est $top [ot_sp_env OT_SPINE_SYM_BUF_PS 45.0] \
    [expr {[ot_sp_env OT_SPINE_SYM_WIRE_PS_UM 0.43]/double($u)}] [ot_sp_env OT_SPINE_SYM_BUF_PS 45.0]
  dict set ::ot_hci_applied $port 1
  puts "$::ot_hci_tag same_root=$port ALL_sinks=$total islands=$counts columns=[llength $cols] leaves=[llength $ids] equal_subtree_depth=$height fork=$::ot_hci_fork@$forkxy"
  return $top
}
