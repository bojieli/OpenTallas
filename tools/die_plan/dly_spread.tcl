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
#   OT_DLY_SPREAD_SEG=1  (unset = off, byte-identical)  SEGMENT form (FABLE-FIX-KV-PV XTAP-C 11-20, kit_dly_lockup.py): a hop lockup
#                        latch u_fl_* (DLL / DHL) is a repeater of the chain, and the stages between two latches are ONE station:
#                        the latch-delimited groups of a run sit at equal route fractions (a group that touches an anchor stage sits
#                        at the anchor), the latch mid-hop like any repeater of the hop (half a hop of wire on each side: same-tap hold before it,
#                        T/2 setup after it).  A chain with a latch is always placed, also when its GPL hops are within
#                        reach (GPL spreads the stages of one segment over taps).  A run without a latch keeps the forms above.
#   OT_DLY_SPREAD_MAX_STAGES  (64; 1024 in SEGMENT form)  longest chain walked
#   STATION reach (KV-PLAN-R1 11-20, CBC 300 um rule): with OT_DLY_SPREAD_STATION_UM set, a chain counts as inside the reach only
#                        when every hop is within min(::ot_dly_min_hop_um, S): the station form also re-spreads 300-405 um
#                        chains instead of leaving them at their GPL hops (kv3_pv D25e3: 15/16 types kept hops up to 406 um).
#   REPEATER ANCHOR (KV-PLAN-R1 11-20, FABLE-CLOSURE 09:05 lever 8): a chain whose stage hops are inside the reach is not
#                        re-spread, but every movable BUF / INV / HB repeater of one of its hops whose detour off that hop
#                        (|a-r| + |r-b| - |a-b|) is over OT_DLY_REP_DETOUR_UM (20) goes to its fraction of the hop, as in a
#                        re-spread chain: a cell on a relay trunk sits between its driver and its sink register.
#                        kv3_pv v8j: the mapped inverter of a pad tail hop sat 1,909 um from both ends (hop 192 um, -8,287 ps).
#   OT_DLY_SPREAD_RE     discovery regexp (default: any <inst>.g_reg.r[k][b] / <inst>.r[k][b] / <inst>.q[b])
# Flops that are FIRM/LOCKED or sited by the plan (ot_face_flops.txt) are anchors, never moved; a run of movable stages between
# two anchors is spread between them.
# A chain whose stages are all plan-sited has nothing to spread and never fails the gate.
# Log: OT_DLY_SPREAD chains C stages S moved M max_hop A -> B um (over reach X -> Y), worst/ideal R, fail F
# DLY-REPAIR-1 (CORE-LIB-LIMITS-1330 11-20, QC cbf_q01_s2): (1) a hop that ends on an anchor which also starts the next run
#   took f1 = 0.0 (the next run's start overwrote fr[anchor]), so its repeaters went BACKWARDS along the route, away from the
#   anchor (cbf: wire bufs 100-760 um onto the u_t12 halo, last hop 902 um, 4.0 ns slew).  Each hop now uses its own run's
#   0.0 / 1.0 at the run ends.  (2) No clear route around the cores -> the chain / repeater keeps its GPL site (counted
#   noroute); the old straight-line fallback put cells inside a core and ds_put snapped them onto its edge.
#   (3) This pass moves cells AFTER the place repair_design, so it repairs the signal nets of the cells it moved
#   (repair_design with every other net dont_touch; CAP_MARGIN / SLEW_MARGIN / OT_PLACE_MAX_TRANSITION as in place).
#   OT_DLY_SPREAD_REPAIR=0 turns (3) off; a session without liberty skips it.
uplevel #0 {
set ds_blk [ord::get_db_block]
set ds_dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set ds_core [$ds_blk getCoreArea]
set ds_halo [expr {round(9.0 * $ds_dbu)}]
set ds_minum [expr {[info exists ::ot_dly_min_hop_um] ? $::ot_dly_min_hop_um : 405.0}]
set ds_min [expr {round($ds_minum * $ds_dbu)}]
set ds_st [expr {[info exists ::env(OT_DLY_SPREAD_STATION_UM)] && [string is double -strict $::env(OT_DLY_SPREAD_STATION_UM)] && $::env(OT_DLY_SPREAD_STATION_UM) > 0 ? round($::env(OT_DLY_SPREAD_STATION_UM) * $ds_dbu) : 0}]
if {$ds_st > 0 && $ds_st < $ds_min} { set ds_min $ds_st }
set ds_rdet [expr {round(([info exists ::env(OT_DLY_REP_DETOUR_UM)] && [string is double -strict $::env(OT_DLY_REP_DETOUR_UM)] ? $::env(OT_DLY_REP_DETOUR_UM) : 20.0) * $ds_dbu)}]
set ds_nrep 0
set ds_ratio [expr {[info exists ::ot_dly_fail_ratio] ? $::ot_dly_fail_ratio : 1.5}]
set ds_seg [expr {[info exists ::env(OT_DLY_SPREAD_SEG)] && $::env(OT_DLY_SPREAD_SEG) eq "1"}]
set ds_maxst [expr {[info exists ::env(OT_DLY_SPREAD_MAX_STAGES)] && [string is integer -strict $::env(OT_DLY_SPREAD_MAX_STAGES)] ? $::env(OT_DLY_SPREAD_MAX_STAGES) : ($ds_seg ? 1024 : 64)}]
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
proc ds_islk {i} { global ds_seg; if {!$ds_seg} { return 0 }; set m [[$i getMaster] getName]; return [expr {([string match "DLL*" $m] || [string match "DHL*" $m]) && [regexp {(^|[./])u_fl_} [$i getName]]}] }
proc ds_isrep {i} { set m [[$i getMaster] getName]; return [expr {![[$i getMaster] isBlock] && ([string match "BUF*" $m] || [string match "INV*" $m] || [string match "HB*" $m] || [ds_islk $i])}] }
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
  dict set ::ds_moved [$inst getName] $inst
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
# ROUTE-END-OUT (KV-PV-FANOUT 11-24): a route end inside a hard macro (a macro pin, or the load centroid of tail copies that ring
# a core group) made every candidate route hit that macro, so the chain was counted NOROUTE and kept its GPL clump at the load
# end (kv3_pv_v6 A5t3 probe: 359 of 424 NOROUTE chains; u_pd41_i_pvw_u_ctl_cmd_0_t_43, 41 stages, hop 679 um; the kit_dly_ram
# lead u_pd3_ram_pdram_3_93, 3 stages at the RAM, 1157 um from its bin).  Such an end now moves to the nearest point of the halo
# box of that macro (repeated while it lands in another macro, at most 4 times, inside the core area); the last hop still runs
# from there to the real pin / loads, and an end that cannot be moved stays as before.  OT_DLY_SPREAD_END_OUT=0 = old behaviour.
set ds_endout [expr {!([info exists ::env(OT_DLY_SPREAD_END_OUT)] && $::env(OT_DLY_SPREAD_END_OUT) eq "0")}]
proc ds_out {p} {
  global ds_mac ds_halo ds_core ds_endout
  if {!$ds_endout} { return $p }
  for {set it 0} {$it < 4} {incr it} {
    lassign $p x y; set moved 0
    foreach m $ds_mac {
      lassign $m a b c d
      if {$x > $a+$ds_halo+2000 && $x < $c-$ds_halo-2000 && $y > $b+$ds_halo+2000 && $y < $d-$ds_halo-2000} {
        set cand {}
        foreach q [lsort -real -index 0 [list [list [expr {$x-$a}] $a $y] [list [expr {$c-$x}] $c $y] [list [expr {$y-$b}] $x $b] [list [expr {$d-$y}] $x $d]]] {
          lassign $q _ qx qy
          if {$qx >= [$ds_core xMin] && $qx <= [$ds_core xMax] && $qy >= [$ds_core yMin] && $qy <= [$ds_core yMax]} { set cand [list $qx $qy]; break }
        }
        if {$cand eq {}} { return $p }
        set p $cand; set moved 1; break
      }
    }
    if {!$moved} { return $p }
  }
  return $p
}
proc ds_route {A B} {
  global ds_xs ds_ys ds_rcache
  set A [ds_out $A]; set B [ds_out $B]
  set q [expr {20 * 1000}]
  lassign $A hx hy; lassign $B tx ty
  set key [list [expr {int($hx/$q)}] [expr {int($hy/$q)}] [expr {int($tx/$q)}] [expr {int($ty/$q)}]]
  if {[dict exists $ds_rcache $key]} {
    # the cached route was found for the quantised pair of its first query: reuse its street lines, keep this pair's end points
    set r [dict get $ds_rcache $key]
    if {$r eq {}} { return {} }
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
  # DLY-REPAIR-1 (2): no clear route -> {} (the caller keeps the GPL sites); never a straight line through a core
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
# REPEATER ANCHOR: repeaters of hop j (0 = before the head, backwards; j >= 1 after stage j) of a chain that keeps its stage sites
proc ds_repfix {P hb segb n} {
  global ds_rdet ds_nrep
  for {set j 0} {$j <= $n} {incr j} {
    if {$j == 0} { set bs {}; set k 0; foreach b $hb { lappend bs [list $k $b]; incr k } } else { set bs [lindex $segb [expr {$j-1}]] }
    if {![llength $bs]} continue
    set a [lindex $P $j]; set b [lindex $P [expr {$j+1}]]
    set md 0; foreach x $bs { set md [expr {max($md, [lindex $x 0])}] }
    set rt {}
    foreach x $bs {
      lassign $x d bi
      if {![ds_movable $bi]} continue
      set c [ds_ctr [$bi getBBox]]
      if {[ds_md $a $c] + [ds_md $c $b] - [ds_md $a $b] <= $ds_rdet} continue
      if {$rt eq {}} { set rt [ds_route $a $b]; if {$rt eq {}} { incr ::ds_noroute; break } }
      if {$j == 0} { set f [expr {1.0 - double($d+1)/($md+2)}] } else { set f [expr {double($d+1)/($md+2)}] }
      lassign [ds_atpl $rt $f] x y
      ds_put $bi $x $y; incr ds_nrep
    }
  }
}
proc ds_main {} {
global ds_blk ds_dbu ds_core ds_min ds_ratio ds_re ds_mac ds_sited ds_st ds_seg ds_maxst ds_nrep ds_rdet
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
  while {[dict exists $ds_next [$cur getName]] && [incr guard] < $ds_maxst} {
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
  # SEGMENT form: lkh[j-1] = 1 when the hop after stage j (1 <= j < n) carries a hop lockup latch
  set lkh {}; set haslk 0
  if {$ds_seg} {
    for {set j 1} {$j < $n} {incr j} {
      set h 0; foreach b_ [lindex $segb [expr {$j-1}]] { if {[ds_islk [lindex $b_ 1]]} { set h 1; break } }
      lappend lkh $h; if {$h} { set haslk 1 }
    }
  }
  set rts {}
  if {!($wb <= $ds_min && !$haslk)} {
    set anch [list 0]
    for {set k 1} {$k <= $n} {incr k} { if {![ds_movable [lindex $seq [expr {$k-1}]]]} { lappend anch $k } }
    lappend anch [expr {$n+1}]
    for {set a 0} {$a < [llength $anch]-1} {incr a} {
      set rt_ [ds_route [lindex $P [lindex $anch $a]] [lindex $P [lindex $anch [expr {$a+1}]]]]
      if {$rt_ eq {}} { set rts {}; break }
      lappend rts $rt_
    }
  }
  # Use the direct span for an unchanged chain. Routed runs below replace both
  # the length and the number of hops with their measured values.
  set rlen [ds_md $src $T]
  set nhop [expr {$n + 1}]
  set nmovable 0
  if {$wb <= $ds_min && !$haslk} { set wa $wb; ds_repfix $P $hb $segb $n } elseif {![llength $rts]} {
    # DLY-REPAIR-1 (2): no clear route for a run: the chain keeps its GPL sites
    set wa $wb; incr ::ds_noroute
  } else {
    # anchors: indexes (0 = src, n+1 = T) plus every stage that is not movable; run of movable stages between anchors -> equal hops
    foreach s_ $seq { if {[ds_movable $s_]} { incr nmovable } }
    # one route per run (anchor -> anchor), around the hard cores; stage k of a run at (k-k0)/(k1-k0) of its length
    set runs {}; set hoprun {}; set rlen 0; set fr [dict create]; set nhop 0
    for {set a 0} {$a < [llength $anch]-1} {incr a} {
      set k0 [lindex $anch $a]; set k1 [lindex $anch [expr {$a+1}]]
      set rt [lindex $rts $a]
      lappend runs [list $k0 $k1 $rt]; set rlen [expr {$rlen + [ds_plen $rt]}]
      for {set j $k0} {$j < $k1} {incr j} { dict set hoprun $j $a }
      # route fraction of every point of the run: equal hops, or (STATION form) ns stations with the stages grouped on them
      set nr [expr {$k1 - $k0 - 1}]; set ns $nr
      if {$ds_st > 0} { set ns [expr {max(1, int(ceil([ds_plen $rt] / double($ds_st))) - 1)}]; if {$ns >= $nr} { set ns $nr } }
      set runlk 0
      if {$haslk && $nr > 0} { for {set j [expr {max(1, $k0)}]} {$j < $k1 && $j < $n} {incr j} { if {[lindex $lkh [expr {$j-1}]]} { set runlk 1; break } } }
      if {$runlk} {
        # groups of the run's movable stages k0+1 .. k1-1, cut at every latch hop; ga / gb: the first / last group has no latch
        # between it and the anchor STAGE k0 / k1, so it sits at that anchor
        set gid {}; set g 0
        for {set k [expr {$k0+1}]} {$k < $k1} {incr k} { if {$k > $k0+1 && [lindex $lkh [expr {$k-2}]]} { incr g }; dict set gid $k $g }
        set ng [expr {$g + 1}]
        set ga [expr {$k0 >= 1 && ![lindex $lkh [expr {$k0-1}]]}]
        set gb [expr {$k1 <= $n && ![lindex $lkh [expr {$k1-2}]]}]
        if {$ng == 1 && $ga && $gb} { set gb 0 }
        set nfree [expr {$ng - $ga - $gb}]
        dict set fr $k0 0.0; dict set fr $k1 1.0; incr nhop [expr {$nfree + 1}]
        for {set k [expr {$k0+1}]} {$k < $k1} {incr k} {
          set g [dict get $gid $k]
          if {$ga && $g == 0} { dict set fr $k 0.0 } elseif {$gb && $g == $ng - 1} { dict set fr $k 1.0 } else { dict set fr $k [expr {double($g - $ga + 1) / ($nfree + 1)}] }
        }
      } else {
      dict set fr $k0 0.0; dict set fr $k1 1.0; incr nhop [expr {$ns + 1}]
      for {set k [expr {$k0+1}]} {$k < $k1} {incr k} {
        if {$ns == $nr} { dict set fr $k [expr {double($k-$k0)/($k1-$k0)}] } else { dict set fr $k [expr {double(int(($k-$k0-1) * $ns / $nr) + 1) / ($ns + 1)}] }
      }
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
        # DLY-REPAIR-1 (1): the run's own ends (an anchor shared with the next run holds that run's 0.0 in fr)
        set f0 [expr {$j == $k0 ? 0.0 : [dict get $fr $j]}]; set f1 [expr {$j + 1 == $k1 ? 1.0 : [dict get $fr [expr {$j+1}]]}]
        lassign [ds_atpl $rt [expr {$f0 + $f * ($f1 - $f0)}]] x y
        ds_put $bi $x $y
      }
    }
    set wa 0; for {set k 1} {$k < [llength $P]} {incr k} { set wa [expr {max($wa, [ds_md [lindex $P [expr {$k-1}]] [lindex $P $k]])}] }
  }
  lappend ::ds_fin [list $head $seq $tl]
  set ds_ha [expr {max($ds_ha, $wa)}]; if {$wa > $ds_min} { incr ds_oa }
  if {[info exists ::env(OT_DLY_SPREAD_DEBUG)] && [string match $::env(OT_DLY_SPREAD_DEBUG) $nm]} { puts "OT_DLY_SPREAD DEBUG [ds_clean $nm] stages $n loads [llength $tl] hops [format %.0f [expr {$wb/double($ds_dbu)}]] -> [format %.0f [expr {$wa/double($ds_dbu)}]] um" }
  set ideal [expr {$rlen / double($nhop)}]   ;# route length: a detour around a core is not a defect
  if {$ideal > 0} {
    set r [expr {$wa / $ideal}]
    if {$r > $ds_wr} { set ds_wr $r }
    if {$wa > $ds_min && $r > $ds_ratio && $nmovable > 0} { incr ds_nfail; if {$ds_nfail <= 5} { puts "OT_DLY_SPREAD WORST [ds_clean [$head getName]] stages $n hop [format %.0f [expr {$wa/double($ds_dbu)}]] um ideal [format %.0f [expr {$ideal/double($ds_dbu)}]] um" } }
  }
}
# FINAL (OPUS-FIX-KV-PV-R4 11-20, report only): the hops above are measured when THAT chain is placed; a later chain can still
# move its tail loads or its source (kv3_pv_v8 v8p: u_bin_i_pvw__u_ctl_cmd q[31] logged 1,228 um, its two loads are the heads of
# pad trunk chains spread after it; placed hop 222 um).  This re-measures every chain on the final sites; the fail gate is unchanged.
set fa 0; set fo 0; set fw ""; set fn 0
foreach c $::ds_fin {
  lassign $c head seq tl
  lassign [ds_back $head] _ src _
  if {$src eq {}} continue
  set sx 0; set sy 0; foreach l $tl { lassign [ds_xy $l] x y; set sx [expr {$sx+$x}]; set sy [expr {$sy+$y}] }
  set P [list $src]; foreach s $seq { lappend P [ds_ctr [$s getBBox]] }; lappend P [list [expr {$sx/[llength $tl]}] [expr {$sy/[llength $tl]}]]
  set w 0; for {set k 1} {$k < [llength $P]} {incr k} { set w [expr {max($w, [ds_md [lindex $P [expr {$k-1}]] [lindex $P $k]])}] }
  if {$w > $ds_min} { incr fo }
  if {$w > $fa} { set fa $w; set fw [ds_clean [$head getName]]; set fn [llength $seq] }
}
puts "OT_DLY_SPREAD FINAL max_hop [format %.0f [expr {$fa/double($ds_dbu)}]] um on final sites (chains over [format %.0f [expr {$ds_min/double($ds_dbu)}]] um: $fo) worst $fw stages $fn"
puts "OT_DLY_SPREAD NOROUTE $::ds_noroute chains / repeaters kept at their GPL sites (no clear route around the cores)"
puts "OT_DLY_SPREAD REPFIX repeaters $ds_nrep moved onto their hop (detour > [format %.0f [expr {$ds_rdet/double($ds_dbu)}]] um)"
puts "OT_DLY_SPREAD chains $ds_nch stages $ds_nst moved $ds_nmv skipped $ds_nskip max_hop [format %.0f [expr {$ds_hb/double($ds_dbu)}]] -> [format %.0f [expr {$ds_ha/double($ds_dbu)}]] um (chains over [format %.0f [expr {$ds_min/double($ds_dbu)}]] um: $ds_ob -> $ds_oa) worst/ideal [format %.2f $ds_wr] fail $ds_nfail"
if {$ds_nfail > 0 && (![info exists ::env(OT_DLY_SPREAD)] || $::env(OT_DLY_SPREAD) ne "warn")} {
  puts "OT_DLY_SPREAD FAIL: $ds_nfail chain(s) keep a hop over $ds_ratio x their ideal hop and over the reach (OT_DLY_SPREAD=warn downgrades)"
  error "OT_DLY_SPREAD: $ds_nfail chains over ratio"
}
}
set ::ds_moved [dict create]; set ::ds_noroute 0; set ::ds_fin {}
ds_main
# DLY-REPAIR-1 (3): repair the signal nets of the moved cells (the place repair_design ran before this pass)
proc ds_repair {} {
  if {[info exists ::env(OT_DLY_SPREAD_REPAIR)] && $::env(OT_DLY_SPREAD_REPAIR) eq "0"} { puts "OT_DLY_SPREAD_REPAIR off"; return }
  if {![dict size $::ds_moved]} { puts "OT_DLY_SPREAD_REPAIR nets 0 (nothing moved)"; return }
  if {![llength [info commands repair_design]] || [catch {llength [get_libs -quiet *]} nl] || $nl == 0} { puts "OT_DLY_SPREAD_REPAIR skipped: no liberty in this session"; return }
  set blk [ord::get_db_block]
  set keep [dict create]
  dict for {nm i} $::ds_moved {
    foreach it [$i getITerms] {
      set n [$it getNet]
      if {$n eq "NULL" || [$n getSigType] ne "SIGNAL" || [$n isSpecial] || [$n isDoNotTouch]} continue
      dict set keep [$n getId] 1
    }
  }
  set masked {}
  foreach n [$blk getNets] { if {[dict exists $keep [$n getId]] || [$n isDoNotTouch]} continue; $n setDoNotTouch 1; lappend masked $n }
  set pmt 320
  if {[info exists ::env(OT_PLACE_MAX_TRANSITION)] && $::env(OT_PLACE_MAX_TRANSITION) ne ""} { set pmt $::env(OT_PLACE_MAX_TRANSITION) }
  if {[string is double -strict $pmt] && $pmt > 0} { set_max_transition $pmt [current_design] }
  set args {}
  if {[info exists ::env(CAP_MARGIN)] && $::env(CAP_MARGIN) ne ""} { lappend args -cap_margin $::env(CAP_MARGIN) }
  if {[info exists ::env(SLEW_MARGIN)] && $::env(SLEW_MARGIN) ne ""} { lappend args -slew_margin $::env(SLEW_MARGIN) }
  set n0 [sta::network_leaf_instance_count]
  puts "OT_DLY_SPREAD_REPAIR repair_design $args on [dict size $keep] nets of [dict size $::ds_moved] moved cells ([llength $masked] other nets dont_touch)"
  set rc [catch {estimate_parasitics -placement; repair_design {*}$args} err opts]
  foreach n $masked { $n setDoNotTouch 0 }
  puts "OT_DLY_SPREAD_REPAIR leaf instances $n0 -> [sta::network_leaf_instance_count]"
  if {$rc} { return -options $opts $err }
}
ds_repair
}
