# S81-BKSEL-RF vB 11-05 (PRE_GLOBAL_PLACE, after face_flops.tcl): short-reach placement of three register groups.
#  (1) u_q.sq[0..831] (the first flop after the 16 hist banks: gsum direct, gbin via the 8-bank OR) sits FIRM beside
#      its bank pin(s): bank pin centre (or the centroid of the driving bank pins for gbin), pushed out of every macro
#      + halo.  rfh6: bank clk->q 416 ps + 470 ps of wire to sq (TT -103); the long wire moves to sq -> sq1 (full cycle).
#  (2) u_q.sq1[i] / u_q.oq1[i] sit FIRM next to the out-face flop they drive (sq1 -> negedge out flop = half cycle).
#  (3) lane_p / f_c_p / f_cr_p / rst_p (the posedge stage after the negedge in-face flop: half cycle) sit FIRM next to
#      the face flop that drives them.
# Function unchanged (placement only).  Released to PLACED by bank_regs_release.tcl before DPL.
uplevel #0 {
set br_blk [ord::get_db_block]
set br_dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set br_core [$br_blk getCoreArea]
set br_cx0 [$br_core xMin]; set br_cy0 [$br_core yMin]; set br_cx1 [$br_core xMax]; set br_cy1 [$br_core yMax]
set br_halo [expr {round(6.0*$br_dbu)}]
set br_macros {}
foreach i [$br_blk getInsts] {
  if {[[$i getMaster] isBlock]} { set b [$i getBBox]; lappend br_macros [list [expr {[$b xMin]-$br_halo}] [expr {[$b yMin]-$br_halo}] [expr {[$b xMax]+$br_halo}] [expr {[$b yMax]+$br_halo}]] }
}
proc br_clamp {x y} {
  global br_cx0 br_cy0 br_cx1 br_cy1 br_dbu
  set m [expr {round(3*$br_dbu)}]
  return [list [expr {max($br_cx0+$m, min($br_cx1-$m-round(2*$br_dbu), $x))}] [expr {max($br_cy0+$m, min($br_cy1-$m, $y))}]]
}
# push a point out of every macro+halo box (nearest edge), a few passes
proc br_out {x y} {
  global br_macros
  for {set k 0} {$k < 6} {incr k} {
    set moved 0
    foreach bb $br_macros {
      lassign $bb x0 y0 x1 y1
      if {$x > $x0 && $x < $x1 && $y > $y0 && $y < $y1} {
        set d [list [expr {$x-$x0}] l [expr {$x1-$x}] r [expr {$y-$y0}] b [expr {$y1-$y}] t]
        set best [lindex [lsort -integer -stride 2 -index 0 $d] 1]
        switch $best { l {set x $x0} r {set x $x1} b {set y $y0} t {set y $y1} }
        set moved 1
      }
    }
    if {!$moved} break
  }
  return [br_clamp $x $y]
}
proc br_is_ff {i} { return [string match "*DFF*" [[$i getMaster] getName]] }
proc br_dnet {i} { foreach it [$i getITerms] { if {[[$it getMTerm] getName] eq "D"} { return [$it getNet] } }; return "NULL" }
proc br_qnet {i} { foreach it [$i getITerms] { set n [[$it getMTerm] getName]; if {$n eq "QN" || $n eq "Q"} { return [$it getNet] } }; return "NULL" }
proc br_driver {net} {
  if {$net eq "NULL" || $net eq ""} { return "" }
  foreach it [$net getITerms] { if {[[$it getMTerm] getIoType] eq "OUTPUT"} { return $it } }
  return ""
}
proc br_itxy {it} { set b [$it getBBox]; return [list [expr {([$b xMin]+[$b xMax])/2}] [expr {([$b yMin]+[$b yMax])/2}]] }
# backward cone of a net through comb std cells (depth <= 5): the macro output pins and flops it reaches
proc br_back {net} {
  set todo [list [list $net 0]]; set seen {}; set pins {}; set ffs {}
  while {[llength $todo]} {
    lassign [lindex $todo 0] n d; set todo [lrange $todo 1 end]
    if {$n eq "NULL" || $n eq "" || [dict exists $seen $n]} continue
    dict set seen $n 1
    set it [br_driver $n]
    if {$it eq ""} continue
    set i [$it getInst]
    if {[[$i getMaster] isBlock]} { lappend pins $it; continue }
    if {[br_is_ff $i]} { lappend ffs $i; continue }
    if {$d >= 5} continue
    foreach jt [$i getITerms] {
      if {[$jt getSigType] ne "SIGNAL" || [[$jt getMTerm] getIoType] ne "INPUT"} continue
      lappend todo [list [$jt getNet] [expr {$d+1}]]
    }
  }
  return [list $pins $ffs]
}
proc br_fwd_ff {net} {
  # first flop reached forward through BUF/INV only
  set todo [list $net]; set seen {}
  while {[llength $todo]} {
    set n [lindex $todo 0]; set todo [lrange $todo 1 end]
    if {$n eq "NULL" || $n eq "" || [dict exists $seen $n]} continue
    dict set seen $n 1
    foreach it [$n getITerms] {
      if {[[$it getMTerm] getIoType] ne "INPUT"} continue
      set i [$it getInst]
      if {[br_is_ff $i]} { return $i }
      set m [[$i getMaster] getName]
      if {[string match "BUF*" $m] || [string match "INV*" $m] || [string match "HB*" $m]} {
        foreach o [$i getITerms] { if {[[$o getMTerm] getIoType] eq "OUTPUT"} { lappend todo [$o getNet] } }
      }
    }
  }
  return ""
}
proc br_center {i} { set b [$i getBBox]; return [list [expr {([$b xMin]+[$b xMax])/2}] [expr {([$b yMin]+[$b yMax])/2}]] }
# step from a face flop toward the core centre by s um
proc br_inward {x y s} {
  global br_cx0 br_cy0 br_cx1 br_cy1 br_dbu
  set d [list [expr {$x-$br_cx0}] l [expr {$br_cx1-$x}] r [expr {$y-$br_cy0}] b [expr {$br_cy1-$y}] t]
  set f [lindex [lsort -integer -stride 2 -index 0 $d] 1]
  set s [expr {round($s*$br_dbu)}]
  switch $f { l {incr x $s} r {incr x -$s} b {incr y $s} t {incr y -$s} }
  return [list $x $y]
}
set br_list {}
set br_n [dict create sq_pin 0 sq_or 0 sq_none 0 q1 0 q1_none 0 inp 0 inp_none 0]
proc br_put {i x y tag} {
  global br_list br_n
  lassign [br_out $x $y] x y
  $i setLocation $x $y
  $i setPlacementStatus FIRM
  lappend br_list [$i getName]
  dict incr br_n $tag
}
set br_dist_max 0
foreach i [$br_blk getInsts] {
  set nm [string map {"\\" ""} [$i getName]]
  if {![br_is_ff $i]} continue
  if {[regexp {^u_q\.sq\[([0-9]+)\]} $nm -> bit] && $bit < 832} {
    lassign [br_back [br_dnet $i]] pins ffs
    if {![llength $pins]} { dict incr br_n sq_none; continue }
    set sx 0; set sy 0
    foreach p $pins { lassign [br_itxy $p] px py; incr sx $px; incr sy $py }
    set x [expr {$sx/[llength $pins]}]; set y [expr {$sy/[llength $pins]}]
    br_put $i $x $y [expr {[llength $pins] == 1 ? "sq_pin" : "sq_or"}]
    lassign [br_center $i] fx fy
    foreach p $pins { lassign [br_itxy $p] px py; set dd [expr {abs($px-$fx)+abs($py-$fy)}]; if {$dd > $br_dist_max} { set br_dist_max $dd } }
  } elseif {[regexp {^(u_q\.(t_s|t_o)|t_s_f|t_o_f)\[} $nm]} {
    set o [br_fwd_ff [br_qnet $i]]
    if {$o eq "" || [$o getPlacementStatus] ne "FIRM"} { dict incr br_n q1_none; continue }
    lassign [br_center $o] x y
    lassign [br_inward $x $y 4.0] x y
    br_put $i $x $y q1
  } elseif {[regexp {^(lane_i|f_c_i|f_cr_i|rst_i)(\[|\$)} $nm]} {
    lassign [br_back [br_dnet $i]] pins ffs
    set src ""
    foreach f $ffs { if {[$f getPlacementStatus] eq "FIRM"} { set src $f; break } }
    if {$src eq ""} { dict incr br_n inp_none; continue }
    lassign [br_center $src] x y
    lassign [br_inward $x $y 4.0] x y
    br_put $i $x $y inp
  }
}
set fh [open $::env(RESULTS_DIR)/ot_bank_regs.txt w]
foreach n $br_list { puts $fh $n }
close $fh
puts "OT_BANK_REGS placed [llength $br_list] FIRM: $br_n; worst bank pin -> sq manhattan [expr {double($br_dist_max)/$br_dbu}] um"
}
