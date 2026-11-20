# DLY-SPREAD (FABLE-GENBUG G8, brief 4.3, 11-15): every generated zero-logic register pipe (ot_dp_dly / ot_pl_pad:
# <inst>.g_reg.r[k][b] / .r[k] ... <inst>.q[b] / .q, names only DISCOVER the candidate flops) that has no plan site is spread on the route
# driver pin -> centroid of its loads.  Stage identity is CONNECTIVITY: stage k+1's D is stage k's Q through BUF/INV/HB only and
# stage k's Q feeds nothing else.  GPL is indifferent to where a flop sits on a fanout-1 chain, so a transport keeps its stages
# at one end (col_h9_r1 u_d10_6_Y: 9 stages over 1,695 um, worst hop 1,268 um, ideal 170).
# Runs after GPL, before DPL (face_flops_release.tcl, after chain_even.tcl).  No netlist change.
#   ::ot_dly_min_hop_um  (405)  a chain whose hops are all within this is left alone
#   ::ot_dly_fail_ratio  (1.5)  after the move, worst hop > ratio * ideal hop (span / (n+1)) -> OT_DLY_SPREAD FAIL
#   OT_DLY_SPREAD_STATION_UM  (unset = off, byte-identical)  STATION form (FABLE-FIX-KV-PV XTAP-A 11-20): the stages of a run go
#                        to ceil(L / S) - 1 stations (at least 1) at equal route fractions instead of one site per stage; stages
#                        of one station sit together, so back-to-back stages share a clock tap and only the station-to-station hops
#                        (each <= S um of route, carrying real wire) can cross a tap.  kv3_pv_v8 v8b: 42,662 of 47,549 FF hold
#                        cross-tap ends were stage k -> k+1 of 100+ stage pad trunks spread at span/(n+1) ~ 10 um per hop.
#                        A run with no more stages than stations keeps the equal spread.
#   OT_DLY_SPREAD_RE     discovery regexp (default: any <inst>.g_reg.r[k][b] / <inst>.r[k][b] / <inst>.q[b])
# Flops that are FIRM/LOCKED or sited by the plan (ot_face_flops.txt) are anchors, never moved; a run of movable stages between
# two anchors is spread between them.
# A chain whose stages are all plan-sited has nothing to spread and never fails the gate.
# Log: OT_DLY_SPREAD chains C stages S moved M max_hop A -> B um (over reach X -> Y), worst/ideal R, fail F
uplevel #0 {
set ds_blk [ord::get_db_block]
set ds_dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set ds_core [$ds_blk getCoreArea]
set ds_halo [expr {round(9.0 * $ds_dbu)}]
set ds_minum [expr {[info exists ::ot_dly_min_hop_um] ? $::ot_dly_min_hop_um : 405.0}]
set ds_min [expr {round($ds_minum * $ds_dbu)}]
set ds_st [expr {[info exists ::env(OT_DLY_SPREAD_STATION_UM)] && [string is double -strict $::env(OT_DLY_SPREAD_STATION_UM)] && $::env(OT_DLY_SPREAD_STATION_UM) > 0 ? round($::env(OT_DLY_SPREAD_STATION_UM) * $ds_dbu) : 0}]
set ds_ratio [expr {[info exists ::ot_dly_fail_ratio] ? $::ot_dly_fail_ratio : 1.5}]
set ds_re [expr {[info exists ::env(OT_DLY_SPREAD_RE)] ? $::env(OT_DLY_SPREAD_RE) : {^(.*?)[./](?:g_reg[./])?(?:r\[[0-9]+\](?:\[[0-9]+\])?|q(?:\[[0-9]+\])?)(?:\$.*|_reg)?$}}]
set ds_mac {}
foreach i [$ds_blk getInsts] { if {[[$i getMaster] isBlock]} { set b [$i getBBox]; lappend ds_mac [list [expr {[$b xMin]-$ds_halo}] [expr {[$b yMin]-$ds_halo}] [expr {[$b xMax]+$ds_halo}] [expr {[$b yMax]+$ds_halo}]] } }
set ds_sited {}
if {[info exists ::env(RESULTS_DIR)] && [file exists $::env(RESULTS_DIR)/ot_face_flops.txt]} {
  set ds_fh [open $::env(RESULTS_DIR)/ot_face_flops.txt r]
  foreach ds_ln [split [read $ds_fh] "\n"] { if {$ds_ln ne ""} { dict set ds_sited [string map {\\ {}} [lindex [split $ds_ln "\t"] 0]] 1 } }
  close $ds_fh
}
proc ds_clean {n} { return [string map {\\ {}} $n] }
proc ds_isff {i} { return [string match "*DFF*" [[$i getMaster] getName]] }
proc ds_isrep {i} { set m [[$i getMaster] getName]; return [expr {![[$i getMaster] isBlock] && ([string match "BUF*" $m] || [string match "INV*" $m] || [string match "HB*" $m])}] }
proc ds_movable {i} { global ds_sited; return [expr {[$i getPlacementStatus] ni {FIRM LOCKED COVER} && ![dict exists $ds_sited [ds_clean [$i getName]]]}] }
proc ds_ctr {b} { return [list [expr {([$b xMin]+[$b xMax])/2}] [expr {([$b yMin]+[$b yMax])/2}]] }
proc ds_xy {o} {
  if {[string match "*dbITerm*" $o]} { set i [$o getInst]; if {[[$i getMaster] isBlock]} { return [ds_ctr [$o getBBox]] }; return [ds_ctr [$i getBBox]] }
  return [ds_ctr [$o getBBox]]
}
proc ds_md {a b} { return [expr {abs([lindex $a 0]-[lindex $b 0]) + abs([lindex $a 1]-[lindex $b 1])}] }
proc ds_outnet {i} { foreach it [$i getITerms] { if {[$it isOutputSignal] && [$it getNet] ne "NULL"} { return [$it getNet] } }; return "" }
# loads of a net through repeaters: {bufs(list of {depth inst}) loads(iterm|bterm)}
proc ds_fwd {net} {
  set bufs {}; set loads {}; set front [list $net]; set d 0
  while {[llength $front] && $d < 40} {
    set nf {}
    foreach n $front {
      if {$n eq "" || $n eq "NULL" || [$n getSigType] ne "SIGNAL"} continue
      foreach bt [$n getBTerms] { lappend loads $bt }
      foreach it [$n getITerms] {
        if {![$it isInputSignal]} continue
        set si [$it getInst]
        if {[ds_isrep $si]} { lappend bufs [list $d $si]; set o [ds_outnet $si]; if {$o ne ""} { lappend nf $o } } else { lappend loads $it }
      }
    }
    set front $nf; incr d
  }
  return [list $bufs $loads]
}
# driver of a flop's D through repeaters: {bufs(from the flop backwards) point inst-or-empty}
proc ds_back {i} {
  set bufs {}; set cur $i
  for {set k 0} {$k < 40} {incr k} {
    set net ""
    foreach it [$cur getITerms] {
      if {[$it isInputSignal] && [$it getNet] ne "NULL" && [[$it getMTerm] getName] ni {CLK RESETN SETN} && [$it getNet] ne ""} { set net [$it getNet]; break }
    }
    if {$net eq "" || [$net getSigType] ne "SIGNAL"} { return [list $bufs {} {}] }
    set drv ""
    foreach o [$net getITerms] { if {[$o isOutputSignal]} { set drv $o } }
    if {$drv eq ""} {
      set bts [$net getBTerms]
      if {[llength $bts]} { return [list $bufs [ds_ctr [[lindex $bts 0] getBBox]] {}] }
      return [list $bufs {} {}]
    }
    set di [$drv getInst]
    if {[[$di getMaster] isBlock]} { return [list $bufs [ds_ctr [$drv getBBox]] {}] }
    if {[ds_isrep $di]} { lappend bufs $di; set cur $di; continue }
    if {![ds_isff $di]} { return [list $bufs {} {}] }   ;# logic driver: a plan item, not a pipe head
    return [list $bufs [ds_ctr [$di getBBox]] $di]
  }
  return [list $bufs {} {}]
}
proc ds_put {inst x y} {
  global ds_mac ds_core
  set w [[$inst getMaster] getWidth]; set h [[$inst getMaster] getHeight]
  foreach m $ds_mac {
    lassign $m a b c d
    if {$x > $a && $x < $c && $y > $b && $y < $d} {
      set best [lsort -real -index 0 [list [list [expr {$x-$a}] $a $y] [list [expr {$c-$x}] $c $y] [list [expr {$y-$b}] $x $b] [list [expr {$d-$y}] $x $d]]]
      lassign [lindex $best 0] _ x y
    }
  }
  set x [expr {max([$ds_core xMin], min([$ds_core xMax]-$w, $x))}]
  set y [expr {max([$ds_core yMin], min([$ds_core yMax]-$h, $y))}]
  $inst setLocation [expr {int($x)}] [expr {int($y)}]
  if {[$inst getPlacementStatus] eq "UNPLACED"} { $inst setPlacementStatus PLACED }
}
proc ds_at {a b f} { return [list [expr {[lindex $a 0]+([lindex $b 0]-[lindex $a 0])*$f}] [expr {[lindex $a 1]+([lindex $b 1]-[lindex $a 1])*$f}]] }


# Manhattan route around the hard cores (core_input_chain.tcl nc_route form): street centre lines = core edges and the gaps between
# macros; the shortest of straight / HVH / VHV / 4-bend routes whose segments clear every macro.  Levels are tried in order, the first
# level with a clear route wins; routes are cached per 20 um quantised end points (bits of one pipe share them).
set ds_xi {}; set ds_yi {}
foreach ds_m $ds_mac { lassign $ds_m a b c d; lappend ds_xi [list [expr {$a + $ds_halo}] [expr {$c - $ds_halo}]]; lappend ds_yi [list [expr {$b + $ds_halo}] [expr {$d - $ds_halo}]] }
proc ds_lines {lo hi ivals} {
  set iv [lsort -integer -index 0 $ivals]; set out {}; set cur $lo
  foreach v $iv { lassign $v a b; if {$a > $cur} { lappend out [expr {($cur + $a) / 2}] }; if {$b > $cur} { set cur $b } }
  if {$hi > $cur} { lappend out [expr {($cur + $hi) / 2}] }
  return $out
}
set ds_xs [ds_lines [$ds_core xMin] [$ds_core xMax] $ds_xi]
set ds_ys [ds_lines [$ds_core yMin] [$ds_core yMax] $ds_yi]
set ds_rcache {}
proc ds_hit {x1 y1 x2 y2} {
  global ds_mac ds_halo
  set e 2000
  foreach m $ds_mac {
    lassign $m a b c d
    set a [expr {$a + $ds_halo}]; set b [expr {$b + $ds_halo}]; set c [expr {$c - $ds_halo}]; set d [expr {$d - $ds_halo}]
    if {$y1 == $y2} { if {$y1 > $b+$e && $y1 < $d-$e && max($x1,$x2) > $a+$e && min($x1,$x2) < $c-$e} { return 1 } } \
    else { if {$x1 > $a+$e && $x1 < $c-$e && max($y1,$y2) > $b+$e && min($y1,$y2) < $d-$e} { return 1 } }
  }
  return 0
}
proc ds_plen {pts} { set l 0; for {set k 1} {$k < [llength $pts]} {incr k} { set l [expr {$l + [ds_md [lindex $pts [expr {$k-1}]] [lindex $pts $k]]}] }; return $l }
proc ds_pok {pts} {
  for {set k 1} {$k < [llength $pts]} {incr k} { lassign [lindex $pts [expr {$k-1}]] a b; lassign [lindex $pts $k] c d; if {[ds_hit $a $b $c $d]} { return 0 } }
  return 1
}
proc ds_route {A B} {
  global ds_xs ds_ys ds_rcache
  set q [expr {20 * 1000}]
  lassign $A hx hy; lassign $B tx ty
  set key [list [expr {int($hx/$q)}] [expr {int($hy/$q)}] [expr {int($tx/$q)}] [expr {int($ty/$q)}]]
  if {[dict exists $ds_rcache $key]} {
    # the cached route was found for the quantised pair of its first query: reuse its street lines, keep this pair's end points
    set r [dict get $ds_rcache $key]
    if {[llength $r] == 2} { return [list $A $B] }
    lset r 0 $A; lset r end $B
    return $r
  }
  set lv {}
  set l1 {}
  foreach x [concat $hx $tx $ds_xs] { lappend l1 [list $A [list $x $hy] [list $x $ty] $B] }
  foreach y [concat $hy $ty $ds_ys] { lappend l1 [list $A [list $hx $y] [list $tx $y] $B] }
  lappend lv $l1
  set l2 {}
  foreach x $ds_xs { foreach y $ds_ys {
    lappend l2 [list $A [list $x $hy] [list $x $y] [list $tx $y] $B]
    lappend l2 [list $A [list $hx $y] [list $x $y] [list $x $ty] $B]
  } }
  lappend lv $l2
  set best {}
  foreach cands $lv {
    set bl 0
    foreach p $cands { if {![ds_pok $p]} continue; set l [ds_plen $p]; if {$best eq {} || $l < $bl} { set best $p; set bl $l } }
    if {$best ne {}} break
  }
  if {$best eq {}} {
    # 4-bend routes via two street lines (the long form): only when nothing shorter clears the cores
    set bl 0
    foreach x1 $ds_xs { foreach y $ds_ys { foreach x2 $ds_xs { set p [list $A [list $x1 $hy] [list $x1 $y] [list $x2 $y] [list $x2 $ty] $B]; if {![ds_pok $p]} continue; set l [ds_plen $p]; if {$best eq {} || $l < $bl} { set best $p; set bl $l } } } }
    foreach y1 $ds_ys { foreach x $ds_xs { foreach y2 $ds_ys { set p [list $A [list $hx $y1] [list $x $y1] [list $x $y2] [list $tx $y2] $B]; if {![ds_pok $p]} continue; set l [ds_plen $p]; if {$best eq {} || $l < $bl} { set best $p; set bl $l } } } }
  }
  if {$best eq {}} { set best [list $A $B] }
  dict set ds_rcache $key $best
  return $best
}
# point at fraction f of the polyline's Manhattan length
proc ds_atpl {pts f} {
  set L [ds_plen $pts]; set want [expr {$f * $L}]; set acc 0
  for {set k 1} {$k < [llength $pts]} {incr k} {
    lassign [lindex $pts [expr {$k-1}]] a b; lassign [lindex $pts $k] c d
    set sg [expr {abs($c-$a) + abs($d-$b)}]
    if {$acc + $sg >= $want && $sg > 0} { set t [expr {double($want-$acc)/$sg}]; return [list [expr {$a+($c-$a)*$t}] [expr {$b+($d-$b)*$t}]] }
    set acc [expr {$acc + $sg}]
  }
  return [lindex $pts end]
}
# the whole pass is one proc: a kit hook shares the global namespace of face_flops_release.tcl, so its loop variables stay local
proc ds_main {} {
global ds_blk ds_dbu ds_core ds_min ds_ratio ds_re ds_mac ds_sited ds_st
# candidates by name (discovery only)
set ds_cand {}
foreach i [$ds_blk getInsts] {
  if {![ds_isff $i]} continue
  if {[regexp $ds_re [ds_clean [$i getName]]]} { dict set ds_cand [$i getName] $i }
}
# successor by connectivity: Q -> repeaters -> exactly one load, the D pin of another candidate (so a stage that also feeds
# logic or a second flop ends the chain: that fan-out is a tail, not a stage)
set ds_next {}; set ds_has_prev {}; set ds_tail {}
dict for {nm i} $ds_cand {
  set o [ds_outnet $i]
  if {$o eq ""} continue
  lassign [ds_fwd $o] bufs loads
  if {[llength $loads] == 1} {
    set l [lindex $loads 0]
    if {[string match "*dbITerm*" $l]} {
      set li [$l getInst]
      if {[dict exists $ds_cand [$li getName]] && [[$l getMTerm] getName] eq "D" && [$li getName] ne $nm && ![dict exists $ds_has_prev [$li getName]]} {
        dict set ds_next $nm [list $li $bufs]; dict set ds_has_prev [$li getName] 1; continue
      }
    }
  }
  dict set ds_tail $nm [list $bufs $loads]
}
set nmovable 0; set rlen 0; set ds_nch 0; set ds_nst 0; set ds_nmv 0; set ds_hb 0; set ds_ha 0; set ds_ob 0; set ds_oa 0; set ds_wr 0; set ds_nfail 0; set ds_nskip 0
dict for {nm head} $ds_cand {
  if {[dict exists $ds_has_prev $nm]} continue
  # walk the chain
  set seq [list $head]; set segb {}; set cur $head; set guard 0
  while {[dict exists $ds_next [$cur getName]] && [incr guard] < 64} {
    lassign [dict get $ds_next [$cur getName]] nx bufs
    lappend segb $bufs; lappend seq $nx; set cur $nx
  }
  set n [llength $seq]
  # tail loads
  if {[dict exists $ds_tail [$cur getName]]} { lassign [dict get $ds_tail [$cur getName]] tb tl } else {
    set o [ds_outnet $cur]; if {$o eq ""} continue
    lassign [ds_fwd $o] tb tl
  }
  lappend segb $tb
  if {![llength $tl]} { incr ds_nskip; if {[info exists ::env(OT_DLY_SPREAD_DEBUG)] && [string match $::env(OT_DLY_SPREAD_DEBUG) $nm]} { puts "OT_DLY_SPREAD DEBUG $nm no loads" }; continue }
  # source: the driver of the head's D (through repeaters); a driver that is not a flop/port/core pin (logic) is a plan item: skip
  lassign [ds_back $head] hb src srcinst
  if {$src eq {}} { incr ds_nskip; if {[info exists ::env(OT_DLY_SPREAD_DEBUG)] && [string match $::env(OT_DLY_SPREAD_DEBUG) $nm]} { puts "OT_DLY_SPREAD DEBUG $nm stages $n no source (logic driver)" }; continue }
  set sx 0; set sy 0
  foreach l $tl { lassign [ds_xy $l] x y; set sx [expr {$sx+$x}]; set sy [expr {$sy+$y}] }
  set T [list [expr {$sx/[llength $tl]}] [expr {$sy/[llength $tl]}]]
  # points of the route before: src, stage centres..., T
  set P [list $src]; foreach s $seq { lappend P [ds_ctr [$s getBBox]] }
  lappend P $T
  set wb 0; for {set k 1} {$k < [llength $P]} {incr k} { set wb [expr {max($wb, [ds_md [lindex $P [expr {$k-1}]] [lindex $P $k]])}] }
  incr ds_nch; incr ds_nst $n
  set ds_hb [expr {max($ds_hb, $wb)}]; if {$wb > $ds_min} { incr ds_ob }
  if {$wb <= $ds_min} { set wa $wb } else {
    # anchors: indexes (0 = src, n+1 = T) plus every stage that is not movable; run of movable stages between anchors -> equal hops
    set nmovable 0; foreach s_ $seq { if {[ds_movable $s_]} { incr nmovable } }
    set anch [list 0]
    for {set k 1} {$k <= $n} {incr k} { if {![ds_movable [lindex $seq [expr {$k-1}]]]} { lappend anch $k } }
    lappend anch [expr {$n+1}]
    # one route per run (anchor -> anchor), around the hard cores; stage k of a run at (k-k0)/(k1-k0) of its length
    set runs {}; set hoprun {}; set rlen 0; set fr [dict create]; set nhop 0
    for {set a 0} {$a < [llength $anch]-1} {incr a} {
      set k0 [lindex $anch $a]; set k1 [lindex $anch [expr {$a+1}]]
      set rt [ds_route [lindex $P $k0] [lindex $P $k1]]
      lappend runs [list $k0 $k1 $rt]; set rlen [expr {$rlen + [ds_plen $rt]}]
      for {set j $k0} {$j < $k1} {incr j} { dict set hoprun $j $a }
      # route fraction of every point of the run: equal hops, or (STATION form) ns stations with the stages grouped on them
      set nr [expr {$k1 - $k0 - 1}]; set ns $nr
      if {$ds_st > 0} { set ns [expr {max(1, int(ceil([ds_plen $rt] / double($ds_st))) - 1)}]; if {$ns >= $nr} { set ns $nr } }
      dict set fr $k0 0.0; dict set fr $k1 1.0; incr nhop [expr {$ns + 1}]
      for {set k [expr {$k0+1}]} {$k < $k1} {incr k} {
        if {$ns == $nr} { dict set fr $k [expr {double($k-$k0)/($k1-$k0)}] } else { dict set fr $k [expr {double(int(($k-$k0-1) * $ns / $nr) + 1) / ($ns + 1)}] }
      }
      for {set k [expr {$k0+1}]} {$k < $k1} {incr k} {
        lassign [ds_atpl $rt [dict get $fr $k]] x y
        ds_put [lindex $seq [expr {$k-1}]] $x $y; incr ds_nmv
        lset P $k [ds_ctr [[lindex $seq [expr {$k-1}]] getBBox]]
      }
    }
    # repeaters of hop j (j = 0: head's D side, backwards; 1..n: after stage j) at their fraction inside the hop, on the run's route
    for {set j 0} {$j <= $n} {incr j} {
      if {$j == 0} { set bs {}; set k 0; foreach b $hb { lappend bs [list $k $b]; incr k } } else { set bs [lindex $segb [expr {$j-1}]] }
      if {![llength $bs]} continue
      lassign [lindex $runs [dict get $hoprun $j]] k0 k1 rt
      set md 0; foreach b $bs { set md [expr {max($md, [lindex $b 0])}] }
      foreach b $bs {
        lassign $b d bi
        if {![ds_movable $bi]} continue
        if {$j == 0} { set f [expr {1.0 - double($d+1)/($md+2)}] } else { set f [expr {double($d+1)/($md+2)}] }
        set f0 [dict get $fr $j]; set f1 [dict get $fr [expr {$j+1}]]
        lassign [ds_atpl $rt [expr {$f0 + $f * ($f1 - $f0)}]] x y
        ds_put $bi $x $y
      }
    }
    set wa 0; for {set k 1} {$k < [llength $P]} {incr k} { set wa [expr {max($wa, [ds_md [lindex $P [expr {$k-1}]] [lindex $P $k]])}] }
  }
  set ds_ha [expr {max($ds_ha, $wa)}]; if {$wa > $ds_min} { incr ds_oa }
  if {[info exists ::env(OT_DLY_SPREAD_DEBUG)] && [string match $::env(OT_DLY_SPREAD_DEBUG) $nm]} { puts "OT_DLY_SPREAD DEBUG [ds_clean $nm] stages $n loads [llength $tl] hops [format %.0f [expr {$wb/double($ds_dbu)}]] -> [format %.0f [expr {$wa/double($ds_dbu)}]] um" }
  set ideal [expr {(($wb <= $ds_min) ? [ds_md $src $T] : $rlen) / double(($wb > $ds_min && $ds_st > 0) ? $nhop : $n + 1)}]   ;# route length: a detour around a core is not a defect
  if {$ideal > 0} {
    set r [expr {$wa / $ideal}]
    if {$r > $ds_wr} { set ds_wr $r }
    if {$wa > $ds_min && $r > $ds_ratio && $nmovable > 0} { incr ds_nfail; if {$ds_nfail <= 5} { puts "OT_DLY_SPREAD WORST [ds_clean [$head getName]] stages $n hop [format %.0f [expr {$wa/double($ds_dbu)}]] um ideal [format %.0f [expr {$ideal/double($ds_dbu)}]] um" } }
  }
}
puts "OT_DLY_SPREAD chains $ds_nch stages $ds_nst moved $ds_nmv skipped $ds_nskip max_hop [format %.0f [expr {$ds_hb/double($ds_dbu)}]] -> [format %.0f [expr {$ds_ha/double($ds_dbu)}]] um (chains over [format %.0f [expr {$ds_min/double($ds_dbu)}]] um: $ds_ob -> $ds_oa) worst/ideal [format %.2f $ds_wr] fail $ds_nfail"
if {$ds_nfail > 0 && (![info exists ::env(OT_DLY_SPREAD)] || $::env(OT_DLY_SPREAD) ne "warn")} {
  puts "OT_DLY_SPREAD FAIL: $ds_nfail chain(s) keep a hop over $ds_ratio x their ideal hop and over the reach (OT_DLY_SPREAD=warn downgrades)"
  error "OT_DLY_SPREAD: $ds_nfail chains over ratio"
}
}
ds_main
}
