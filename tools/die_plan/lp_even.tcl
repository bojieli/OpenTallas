# KV-PVGEN 11-15 (COORD 11-16: FIRM sites for the core_link_pipe stages): PRE_RESIZE (after GPL, before repair_design buffers the hops).
# bind.core_link_pipe puts ot_dp_dly u_pc_lp_<leaf>_<port>_<k> stages on a core<->core hop; wirelength-driven GPL is indifferent to
# where a flop of a fanout-1 chain sits, so it bunches the stages at one end.  Here every chain (instance u_pc_lp_X, bit b: the flops
# X.r[k][b] .. X.q[b]) gets equal hops on the straight line from its driver (pin of the launching core / flop, traced back through
# buffers) to the centroid of its loads (traced forward through buffers): stage j of D at fraction (j+1)/(D+1).  No netlist change; the
# stages are PLACED (DPL legalizes), moved out of macro keep-outs to the nearest edge.  Chains whose worst hop is already <= the reach
# (::ot_lp_min_hop_um, default 0 = always) are left alone.  Report: OT_LP_EVEN lines.
uplevel #0 {
set lp_blk [ord::get_db_block]
set lp_dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set lp_core [$lp_blk getCoreArea]
set lp_halo [expr {round(9.0 * $lp_dbu)}]
set lp_min [expr {[info exists ::ot_lp_min_hop_um] ? round($::ot_lp_min_hop_um * $lp_dbu) : 0}]
set lp_mac {}
foreach i [$lp_blk getInsts] { if {[[$i getMaster] isBlock]} { set b [$i getBBox]; lappend lp_mac [list [expr {[$b xMin]-$lp_halo}] [expr {[$b yMin]-$lp_halo}] [expr {[$b xMax]+$lp_halo}] [expr {[$b yMax]+$lp_halo}]] } }
proc lp_clean {n} { return [string map {\\ {}} $n] }
proc lp_isbuf {inst} { set m [[$inst getMaster] getName]; return [expr {[string match "BUF*" $m] || [string match "INV*" $m] || [string match "HB*" $m]}] }
proc lp_ctr {b} { return [list [expr {([$b xMin]+[$b xMax])/2}] [expr {([$b yMin]+[$b yMax])/2}]] }
proc lp_loc {o} {
  if {[string match "*dbBTerm*" $o]} { return [lp_ctr [$o getBBox]] }
  set inst [$o getInst]
  if {[[$inst getMaster] isBlock]} { if {![catch {set r [$o getAvgXY]}]} { lassign $r ok x y; if {$ok} { return [list $x $y] } } }
  return [lp_ctr [$inst getBBox]]
}
# driver of a net, looking back through buffers
proc lp_driver {net} {
  for {set d 0} {$d < 30} {incr d} {
    set drv ""
    foreach it [$net getITerms] { if {[$it isOutputSignal]} { set drv $it; break } }
    if {$drv eq ""} { foreach bt [$net getBTerms] { return $bt }; return "" }
    set inst [$drv getInst]
    if {![[$inst getMaster] isBlock] && [lp_isbuf $inst]} {
      set nn ""; foreach it [$inst getITerms] { if {[$it isInputSignal] && [$it getNet] ne "NULL"} { set nn [$it getNet] } }
      if {$nn eq ""} { return $drv }; set net $nn; continue
    }
    return $drv
  }
  return ""
}
# loads of a net, forward through buffers
proc lp_loads {net} {
  set out {}; set front [list $net]
  for {set d 0} {$d < 30 && [llength $front]} {incr d} {
    set nf {}
    foreach n $front {
      foreach bt [$n getBTerms] { lappend out $bt }
      foreach it [$n getITerms] {
        if {![$it isInputSignal]} continue
        set si [$it getInst]
        if {![[$si getMaster] isBlock] && [lp_isbuf $si]} { foreach o [$si getITerms] { if {[$o isOutputSignal] && [$o getNet] ne "NULL"} { lappend nf [$o getNet] } } } else { lappend out $it }
      }
    }
    set front $nf
  }
  return $out
}
proc lp_put {inst x y} {
  global lp_mac lp_core
  set w [[$inst getMaster] getWidth]; set h [[$inst getMaster] getHeight]
  foreach m $lp_mac {
    lassign $m a b c d
    if {$x > $a && $x < $c && $y > $b && $y < $d} {
      set best [lsort -real -index 0 [list [list [expr {$x-$a}] $a $y] [list [expr {$c-$x}] $c $y] [list [expr {$y-$b}] $x $b] [list [expr {$d-$y}] $x $d]]]
      lassign [lindex $best 0] _ x y
    }
  }
  set x [expr {max([$lp_core xMin], min([$lp_core xMax]-$w, $x))}]
  set y [expr {max([$lp_core yMin], min([$lp_core yMax]-$h, $y))}]
  $inst setLocation [expr {int($x)}] [expr {int($y)}]
  if {[$inst getPlacementStatus] eq "UNPLACED"} { $inst setPlacementStatus PLACED }
}
proc lp_dnet {inst} { foreach it [$inst getITerms] { if {[[$it getMTerm] getName] eq "D"} { return [$it getNet] } }; return "" }
proc lp_qnet {inst} { foreach it [$inst getITerms] { if {[$it isOutputSignal]} { return [$it getNet] } }; return "" }
# group the stage flops: key = u_pc_lp_X + bit
array set lp_grp {}
foreach i [$lp_blk getInsts] {
  set n [lp_clean [$i getName]]
  if {![regexp {(u_pc_lp_[^.]+)\.(?:r\[[0-9]+\]\[([0-9]+)\]|q\[([0-9]+)\])} $n -> x b1 b2]} continue
  set b [expr {$b1 ne "" ? $b1 : $b2}]
  lappend lp_grp($x,$b) $i
}
set lp_n 0; set lp_moved 0; set lp_skipped 0; set lp_worst0 0; set lp_worst1 0
foreach key [array names lp_grp] {
  set fl $lp_grp($key); set D [llength $fl]
  # order by connectivity: the head stage is the one whose D net is not driven by another flop of the group
  array unset lp_byq; foreach f $fl { set q [lp_qnet $f]; if {$q ne ""} { set lp_byq([$q getName]) $f } }
  set head ""
  foreach f $fl { set dn [lp_dnet $f]; if {$dn eq "" || ![info exists lp_byq([$dn getName])]} { set head $f; break } }
  if {$head eq ""} { incr lp_skipped; continue }
  set seq [list $head]; set cur $head
  for {set k 1} {$k < $D} {incr k} {
    set nxt ""
    foreach l [lp_loads [lp_qnet $cur]] { if {[string match "*dbITerm*" $l] && [lsearch $fl [$l getInst]] >= 0} { set nxt [$l getInst]; break } }
    if {$nxt eq ""} break
    lappend seq $nxt; set cur $nxt
  }
  if {[llength $seq] != $D} { incr lp_skipped; continue }
  set drv [lp_driver [lp_dnet $head]]
  set loads [lp_loads [lp_qnet [lindex $seq end]]]
  if {$drv eq "" || ![llength $loads]} { incr lp_skipped; continue }
  lassign [lp_loc $drv] hx hy
  set sx 0; set sy 0; foreach l $loads { lassign [lp_loc $l] x y; incr sx $x; incr sy $y }
  set tx [expr {$sx/[llength $loads]}]; set ty [expr {$sy/[llength $loads]}]
  # worst hop now
  set px $hx; set py $hy; set w0 0
  foreach s $seq { lassign [lp_ctr [$s getBBox]] x y; set w0 [expr {max($w0, abs($x-$px)+abs($y-$py))}]; set px $x; set py $y }
  set w0 [expr {max($w0, abs($tx-$px)+abs($ty-$py))}]
  incr lp_n
  if {$w0 > $lp_worst0} { set lp_worst0 $w0 }
  if {$w0 <= $lp_min} { if {$w0 > $lp_worst1} { set lp_worst1 $w0 }; incr lp_skipped; continue }
  for {set j 0} {$j < $D} {incr j} {
    set f [expr {double($j+1)/($D+1)}]
    lp_put [lindex $seq $j] [expr {$hx+($tx-$hx)*$f}] [expr {$hy+($ty-$hy)*$f}]
    incr lp_moved
  }
  set px $hx; set py $hy; set w1 0
  foreach s $seq { lassign [lp_ctr [$s getBBox]] x y; set w1 [expr {max($w1, abs($x-$px)+abs($y-$py))}]; set px $x; set py $y }
  set w1 [expr {max($w1, abs($tx-$px)+abs($ty-$py))}]
  if {$w1 > $lp_worst1} { set lp_worst1 $w1 }
}
puts "OT_LP_EVEN chains $lp_n moved_stages $lp_moved left $lp_skipped worst_hop_um before [expr {$lp_worst0/double($lp_dbu)}] after [expr {$lp_worst1/double($lp_dbu)}]"
}
