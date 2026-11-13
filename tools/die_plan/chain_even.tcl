# S81-RCK-4 11-07 (class: register chains left bunched by GPL, SMELL 5/7; relay_mid.tcl comment S81 g3k3 10-24 saw the same):
# wirelength-driven GPL is indifferent to where a flop sits on a straight fanout-1 register chain, so a transport keeps
# its stages at one end and pays the whole distance in one hop (serdes t13: am_ok 1007 um from its FSM; u_txl r->q
# ~1.2 mm).  PRE_DETAIL_PLACE: every chain head -> stages -> tail gets equal hops on the straight line between the GPL
# position of the head and of the tail; buffers on the chain are moved with it.  No netlist change.
#   ::ot_chain_res    = Tcl list of {head_re stage_re}: head flops, chain stage flops (names with backslashes removed)
#   ::ot_chain_groups = optional list of {name from_re {stage_re..} cone_re to_re}: one clustered chain (metadata cohort):
#                       centroid of from_re -> stage_re stages by index -> cone flop(s) -> centroid of to_re
# Both come from /work/chain_even_cfg.tcl (gen_phys, plan type key chain_even).
# R-REACH-5 (RULEBOOK 11-13, RULES-REACH-1; gen_phys.REACH_EVEN_CHAINS, every kit without its own chain_even key):
#   ::ot_chain_min_hop_um  = only a chain with a hop (head -> stage .. -> tail) longer than this is re-spaced (405: a
#                            chain inside the reach is left where GPL put it, so kits without the class are unchanged)
#   ::ot_chain_skip_sited  = 1: flops the plan sited (ot_face_flops.txt: face / station / pad registers that were FIRM
#                            through GPL and were just released) are never moved as stages
uplevel #0 {
set ce_blk [ord::get_db_block]
set ce_dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set ce_top [expr {[info exists ::env(OT_RCK_BAND_TOP_UM)] ? round(($::env(OT_RCK_BAND_TOP_UM) - 3.0) * $ce_dbu) : 2147483647}]
set ce_core [$ce_blk getCoreArea]
set ce_halo [expr {round(9.0 * $ce_dbu)}]
set ce_mac {}
foreach i [$ce_blk getInsts] { if {[[$i getMaster] isBlock]} { set b [$i getBBox]; lappend ce_mac [list [expr {[$b xMin]-$ce_halo}] [expr {[$b yMin]-$ce_halo}] [expr {[$b xMax]+$ce_halo}] [expr {[$b yMax]+$ce_halo}]] } }
proc ce_clean {n} { return [string map {\\ {}} $n] }
proc ce_isff {inst} { return [string match "*DFF*" [[$inst getMaster] getName]] }
proc ce_isbuf {inst} { set m [[$inst getMaster] getName]; return [expr {[string match "BUF*" $m] || [string match "INV*" $m] || [string match "HB*" $m]}] }
set ce_sited {}
if {[info exists ::ot_chain_skip_sited] && $::ot_chain_skip_sited && [info exists ::env(RESULTS_DIR)] && [file exists $::env(RESULTS_DIR)/ot_face_flops.txt]} {
  set ce_fh [open $::env(RESULTS_DIR)/ot_face_flops.txt r]
  foreach ce_ln [split [read $ce_fh] "\n"] { if {$ce_ln ne ""} { dict set ce_sited [string map {\\ {}} [lindex [split $ce_ln "\t"] 0]] 1 } }
  close $ce_fh
}
set ce_min_hop [expr {[info exists ::ot_chain_min_hop_um] ? round($::ot_chain_min_hop_um * $ce_dbu) : 0}]
proc ce_movable {inst} { global ce_sited; return [expr {[$inst getPlacementStatus] ni {FIRM LOCKED COVER} && ![dict exists $ce_sited [string map {\\ {}} [$inst getName]]]}] }
proc ce_ctr {b} { return [list [expr {([$b xMin]+[$b xMax])/2}] [expr {([$b yMin]+[$b yMax])/2}]] }
proc ce_out {inst} { set r {}; foreach it [$inst getITerms] { if {[$it isOutputSignal] && [$it getNet] ne "NULL"} { lappend r [$it getNet] } }; return $r }
# forward trace from a net through buffers: returns {buffers(by depth) loads(iterm)}
proc ce_fwd {net} {
  set bufs {}; set loads {}; set front [list $net]; set d 0
  while {[llength $front] && $d < 40} {
    set nf {}
    foreach n $front {
      if {[$n getSigType] ne "SIGNAL"} continue
      foreach bt [$n getBTerms] { lappend loads $bt }
      foreach it [$n getITerms] {
        if {![$it isInputSignal]} continue
        set si [$it getInst]
        if {![[$si getMaster] isBlock] && [ce_isbuf $si]} { lappend bufs [list $d $si]; foreach o [ce_out $si] { lappend nf $o } } else { lappend loads $it }
      }
    }
    set front $nf; incr d
  }
  return [list $bufs $loads]
}
proc ce_put {inst x y} {
  global ce_mac ce_top ce_core
  set w [[$inst getMaster] getWidth]; set h [[$inst getMaster] getHeight]
  if {$y > $ce_top - $h} { set y [expr {$ce_top - $h}] }
  foreach m $ce_mac {
    lassign $m a b c d
    if {$x > $a && $x < $c && $y > $b && $y < $d} {
      # nearest macro edge
      set best [lsort -real -index 0 [list [list [expr {$x-$a}] $a $y] [list [expr {$c-$x}] $c $y] [list [expr {$y-$b}] $x $b] [list [expr {$d-$y}] $x $d]]]
      lassign [lindex $best 0] _ x y
    }
  }
  set x [expr {max([$ce_core xMin], min([$ce_core xMax]-$w, $x))}]
  set y [expr {max([$ce_core yMin], min([$ce_core yMax]-$h, $y))}]
  $inst setLocation [expr {int($x)}] [expr {int($y)}]
  if {[$inst getPlacementStatus] eq "UNPLACED"} { $inst setPlacementStatus PLACED }
}
proc ce_at {x0 y0 x1 y1 f} { return [list [expr {$x0+($x1-$x0)*$f}] [expr {$y0+($y1-$y0)*$f}]] }
proc ce_loc {o} { if {[string match "*dbBTerm*" $o]} { return [ce_ctr [$o getBBox]] }; if {[string match "*dbITerm*" $o]} { set inst [$o getInst]; if {[[$inst getMaster] isBlock]} { return [ce_ctr [$o getBBox]] }; return [ce_ctr [$inst getBBox]] }; return [ce_ctr [$o getBBox]] }
# one chain from a head flop
proc ce_chain {head re} {
  global ce_st
  set seq [list $head]; set segb {}; set cur $head; set tail {}; set tail_loads {}
  while {1} {
    set nets [ce_out $cur]; if {![llength $nets]} break
    lassign [ce_fwd [lindex $nets 0]] bufs loads
    set next {}
    foreach l $loads { if {[string match "*dbITerm*" $l]} { set li [$l getInst]; if {[ce_isff $li] && [[$l getMTerm] getName] eq "D" && [regexp $re [ce_clean [$li getName]]] && [ce_movable $li]} { set next $li; break } } }
    if {$next ne ""} {
      lappend segb $bufs; lappend seq $next; set cur $next
      if {[llength $seq] > 16} break
      continue
    }
    # terminal: tail = centroid of the real loads
    set sx 0; set sy 0; set n 0
    foreach l $loads { lassign [ce_loc $l] x y; incr sx $x; incr sy $y; incr n }
    if {$n} { set tail [list [expr {$sx/$n}] [expr {$sy/$n}]] }
    set tail_loads $loads
    lappend segb $bufs
    break
  }
  if {$tail eq "" || [llength $seq] < 2} { return 0 }
  set hops [expr {[llength $seq]}]   ;# stages after head + 1 tail hop
  lassign [ce_ctr [$head getBBox]] hx hy; lassign $tail tx ty
  global ce_min_hop
  if {$ce_min_hop > 0} {
    # R-REACH-5: leave a chain whose hops are all inside the reach
    set px $hx; set py $hy; set worst 0
    foreach s [lrange $seq 1 end] { lassign [ce_ctr [$s getBBox]] sx2 sy2; set worst [expr {max($worst, abs($sx2-$px)+abs($sy2-$py))}]; set px $sx2; set py $sy2 }
    set worst [expr {max($worst, abs($tx-$px)+abs($ty-$py))}]
    if {$worst <= $ce_min_hop} { return 0 }
    # ... and never make the worst hop worse by pushing the farthest load of the last stage out (a fan-out bit with loads spread over the
    # type is a copy problem, R-REACH-1, not a chain: S81 leaf t21 lpad q[0], 10 loads, 700 -> 827 um when moved)
    lassign [ce_at $hx $hy $tx $ty [expr {double([llength $seq]-1)/$hops}]] nx ny
    set far_old 0; set far_new 0
    foreach l $tail_loads {
      lassign [ce_loc $l] lx ly
      set far_old [expr {max($far_old, abs($lx-$px)+abs($ly-$py))}]
      set far_new [expr {max($far_new, abs($lx-$nx)+abs($ly-$ny))}]
    }
    if {$far_new > $far_old && $far_new > $worst} { return 0 }
  }
  set old 0; set hp {}
  for {set j 1} {$j < [llength $seq]} {incr j} {
    lassign [ce_at $hx $hy $tx $ty [expr {double($j)/$hops}]] x y
    set inst [lindex $seq $j]
    ce_put $inst $x $y
  }
  # buffers of hop j at their fraction inside the hop
  for {set j 0} {$j < [llength $segb]} {incr j} {
    set bs [lindex $segb $j]; if {![llength $bs]} continue
    set md 0; foreach b $bs { set md [expr {max($md, [lindex $b 0])}] }
    foreach b $bs {
      lassign $b d inst
      if {![ce_movable $inst]} continue
      set f [expr {($j + double($d+1)/($md+2)) / $hops}]
      lassign [ce_at $hx $hy $tx $ty $f] x y
      ce_put $inst $x $y
    }
  }
  return [expr {[llength $seq]-1}]
}
set ce_tot 0; set ce_chains 0
foreach ce_pair $::ot_chain_res {
  lassign $ce_pair ce_hre ce_sre
  set ce_heads {}
  foreach i [$ce_blk getInsts] { if {[ce_isff $i] && [regexp $ce_hre [ce_clean [$i getName]]]} { lappend ce_heads $i } }
  foreach h $ce_heads { set n [ce_chain $h $ce_sre]; if {$n} { incr ce_tot $n; incr ce_chains } }
  puts "OT_CHAIN_EVEN heads [llength $ce_heads] re $ce_hre -> $ce_sre: chains so far $ce_chains stages moved $ce_tot"
}
# clustered metadata cohort (AM count/valid: many-to-one cone in the chain)
if {[info exists ::ot_chain_groups]} {
  foreach ce_g $::ot_chain_groups {
    lassign $ce_g gname from_re stage_list cone_re to_re
    proc ce_cent {re} { global ce_blk; set sx 0; set sy 0; set n 0; foreach i [$ce_blk getInsts] { if {[ce_isff $i] && [regexp $re [ce_clean [$i getName]]]} { lassign [ce_ctr [$i getBBox]] x y; incr sx $x; incr sy $y; incr n } }; if {!$n} { return {} }; return [list [expr {$sx/$n}] [expr {$sy/$n}] $n] }
    set a [ce_cent $from_re]; set z [ce_cent $to_re]
    if {$a eq {} || $z eq {}} { puts "OT_CHAIN_GROUP $gname: no endpoints"; continue }
    lassign $a ax ay; lassign $z zx zy
    set hops [expr {[llength $stage_list]+2}]
    foreach i [$ce_blk getInsts] { if {[ce_isff $i] && [regexp $from_re [ce_clean [$i getName]]]} {
      foreach q [ce_out $i] { lassign [ce_fwd $q] bufs loads; set md 0; foreach b $bufs { set md [expr {max($md,[lindex $b 0])}] }
        foreach b $bufs { lassign $b dd bi; if {[ce_movable $bi]} { lassign [ce_at $ax $ay $zx $zy [expr {double($dd+1)/($md+2)/$hops}]] bx by; ce_put $bi $bx $by } } } } }
    set j 1
    foreach sre $stage_list {
      lassign [ce_at $ax $ay $zx $zy [expr {double($j)/$hops}]] x y
      set nmv 0
      foreach i [$ce_blk getInsts] { if {[ce_isff $i] && [regexp $sre [ce_clean [$i getName]]] && [ce_movable $i]} { ce_put $i $x $y; incr nmv
        foreach q [ce_out $i] { lassign [ce_fwd $q] bufs loads; set md 0; foreach b $bufs { set md [expr {max($md,[lindex $b 0])}] }
          foreach b $bufs { lassign $b dd bi; if {[ce_movable $bi]} { lassign [ce_at $ax $ay $zx $zy [expr {($j + double($dd+1)/($md+2))/$hops}]] bx by; ce_put $bi $bx $by } } } } }
      puts "OT_CHAIN_GROUP $gname stage $j re $sre moved $nmv to [expr {$x/$ce_dbu}] [expr {$y/$ce_dbu}]"
      incr j
    }
    lassign [ce_at $ax $ay $zx $zy [expr {double($j)/$hops}]] x y
    # cone flops + the gates of their fan-in cone back to flops; buffers on their Q go toward the sink centroid
    foreach i [$ce_blk getInsts] {
      if {![ce_isff $i] || ![regexp $cone_re [ce_clean [$i getName]]]} continue
      ce_put $i $x $y
      set front {}; foreach it [$i getITerms] { if {$it ne "NULL" && [$it isInputSignal] && [[$it getMTerm] getName] eq "D"} { lappend front [$it getNet] } }
      set nc 0
      lassign [ce_at $ax $ay $zx $zy [expr {($j-0.5)/$hops}]] cx cy
      for {set d 0} {$d < 24 && [llength $front]} {incr d} {
        set nf {}
        foreach n $front {
          if {$n eq "NULL"} continue
          foreach it [$n getITerms] {
            if {![$it isOutputSignal]} continue
            set di [$it getInst]; if {[ce_isff $di] || [[$di getMaster] isBlock] || ![ce_movable $di]} continue
            ce_put $di $cx $cy; incr nc
            foreach a2 [$di getITerms] { if {[$a2 isInputSignal] && [$a2 getNet] ne "NULL" && [[$a2 getNet] getSigType] eq "SIGNAL"} { lappend nf [$a2 getNet] } }
          }
        }
        set front $nf
      }
      foreach q [ce_out $i] {
        lassign [ce_fwd $q] bufs loads
        set md 0; foreach b $bufs { set md [expr {max($md,[lindex $b 0])}] }
        foreach b $bufs { lassign $b dd bi; if {[ce_movable $bi]} { lassign [ce_at $ax $ay $zx $zy [expr {($j + double($dd+1)/($md+2))/$hops}]] bx by; ce_put $bi $bx $by } }
      }
      puts "OT_CHAIN_GROUP $gname cone [ce_clean [$i getName]] gates $nc at [expr {$x/$ce_dbu}] [expr {$y/$ce_dbu}]"
    }
  }
}
}
