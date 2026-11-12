# GENERATED-COPY of tools/die_plan/leaf_affinity.tcl (POST_CTS, after tap_balance.tcl; FLOW 2026-10-25, cqb/NEARMISS F4).
# Register -> register transfers with NO logic between them (direct Q -> D, or through buffer / inverter cells only:
# pin register -> stage 2, shift chains) have no data delay to absorb clock skew, so any launch / capture leaf skew is
# FF hold slack lost one for one (QC cqb 44 of 107, HBM argmax 274 of 758, S81 ve_m / ve_s / rr_h0 FF misses).
# TritonCTS has no skew groups, so the flow does what a skew group would: every connected group of such registers
# (the zero-logic transfer graph, components up to OT_LEAF_AFF_MAX_GROUP members) is re-hung onto ONE clock leaf --
# the leaf that already drives most members -- if every moved member sits within OT_LEAF_AFF_UM of that leaf's driver
# and the leaf stays <= the largest leaf fanout CTS built (+OT_LEAF_AFF_SLACK).  Only leaf nets of the same clock, driven
# by a clock buffer cell, are used; nothing else changes (no cells added, no data path touched).
# Env: OT_LEAF_AFF_UM (default 30), OT_LEAF_AFF_MAX_GROUP (default 24), OT_LEAF_AFF_SLACK (default 4),
#      OT_LEAF_AFF_DEPTH (buffer / inverter hops followed, default 4), OT_LEAF_AFF_REPORT_ONLY=1 (count, no change).
#      OT_LEAF_AFF_SPLIT_UM (default 30; 0 = off): groups skipped far / big are re-tried as local sub-groups whose flop
#      bbox half-perimeter <= this many um (DIE-S81-85 11-09 class fix; see the LOCAL SPLIT block at the end).
# Prints OT_LEAF_AFF ... summary lines (pairs, cross-leaf before / after, groups moved / skipped by reason).
# The ORFS POST_CTS hook may be sourced inside a procedure. Helper procs
# share these dictionaries/union-find arrays through the global namespace.
global la_d la_ck la_par la_clock
# DIE-S81-85 11-09: la_try (local split pass) reads these through the global namespace too
global la_fo la_cap la_ronly la_moved la_blk la_um la_dbu la_maxg
proc la_env {k d} { expr {[info exists ::env($k)] && $::env($k) ne "" ? $::env($k) : $d} }
set la_um [la_env OT_LEAF_AFF_UM 30.0]
set la_maxg [la_env OT_LEAF_AFF_MAX_GROUP 24]
set la_slack [la_env OT_LEAF_AFF_SLACK 4]
set la_depth [la_env OT_LEAF_AFF_DEPTH 4]
set la_ronly [la_env OT_LEAF_AFF_REPORT_ONLY 0]
# KW-FIX-45 11-12 (COORD, QC coll_n): OT_LEAF_AFF_ASYNC=1 keeps async set/reset pins as zero-logic successors, so a
# reset-release flop and the registers it releases (Q -> buf/inv -> CLR/SET) hang on ONE leaf of their common clock:
# coll_n s25 ECO left 4 removal checks u_rx.r_rst_n -> u_rxcal.u_rc.c[*] at -22 ps (same clk_coll edge tree, two
# leaves).  Default 0 = unchanged (async pins dropped as before).
set la_async [la_env OT_LEAF_AFF_ASYNC 0]
set la_blk [ord::get_db_block]
set la_dbu [[ord::get_db_tech] getDbUnitsPerMicron]

# registers: inst name -> CK iterm; data iterms
set la_ck [dict create]
set la_clock [dict create]
foreach p [all_registers -clock_pins] {
  set it [sta::sta_to_db_pin $p]
  if {$it eq "NULL" || $it eq ""} continue
  # Hard-child sequential abstracts are returned by all_registers too.
  # Their compensated clock pins are not parent CTS leaves and must stay bound.
  if {[[[$it getInst] getMaster] isBlock]} continue
  set name [[$it getInst] getName]
  dict set la_ck $name $it
  set clocks [get_property $p clocks]
  set clock_name ""
  if {[llength $clocks] == 1} { set clock_name [get_full_name [lindex $clocks 0]] }
  dict set la_clock $name $clock_name
}
set la_d [dict create]
foreach p [all_registers -data_pins] {
  set it [sta::sta_to_db_pin $p]
  if {$it eq "NULL" || $it eq ""} continue
  dict set la_d [$it getInst]:[[$it getMTerm] getName] 1
}
foreach p [all_registers -async_pins] {
  set it [sta::sta_to_db_pin $p]
  if {$it eq "NULL" || $it eq ""} continue
  if {$la_async} {
    dict set la_d [$it getInst]:[[$it getMTerm] getName] 1
  } else {
    dict unset la_d [$it getInst]:[[$it getMTerm] getName]
  }
}
proc la_is_bufinv {inst} { regexp {^(BUF|INV|HB|CKINV|CKBUF)} [[$inst getMaster] getName] }
proc la_outs {inst} {
  set o {}
  foreach it [$inst getITerms] { if {[$it isOutputSignal] && [$it getNet] ne "NULL"} { lappend o $it } }
  return $o
}
# Clock net type alone does not establish domain identity. Reconnecting a clock
# pin across distinct roots changes behavior even when the data path is short.
proc la_same_clock {members} {
  global la_clock
  set expected ""
  foreach name $members {
    if {![dict exists $la_clock $name] || [dict get $la_clock $name] eq ""} { return 0 }
    set current [dict get $la_clock $name]
    if {$expected ne "" && $current ne $expected} { return 0 }
    set expected $current
  }
  return [expr {$expected ne ""}]
}
# zero-logic successors of register R: registers whose data pin is reached through nets and buf/inv cells only
proc la_succ {inst depth} {
  global la_d la_ck
  set res {}
  foreach o [la_outs $inst] {
    set n [$o getNet]
    if {[$n getSigType] in {POWER GROUND CLOCK}} continue
    foreach it [$n getITerms] {
      if {![$it isInputSignal]} continue
      set si [$it getInst]
      if {[dict exists $la_d $si:[[$it getMTerm] getName]] && [dict exists $la_ck [$si getName]]} {
        lappend res [$si getName]
      } elseif {$depth > 0 && [la_is_bufinv $si]} {
        lappend res {*}[la_succ $si [expr {$depth - 1}]]
      }
    }
  }
  return $res
}
proc la_leaf {name} {
  global la_ck
  set n [[dict get $la_ck $name] getNet]
  return $n
}
proc la_drv {net} {
  foreach it [$net getITerms] { if {[$it isOutputSignal]} { return [$it getInst] } }
  return ""
}
proc la_xy {inst} { lassign [$inst getLocation] x y; return [list $x $y] }
# Gating identity of a clock leaf: follow the leaf's driver upstream through clock buffers / inverters to the
# first cell that is not one (an ICG, a clock mux, a divider flop) or to a port, counting inverter parity.
# STA reports the same clock name before and after an integrated clock gate, so la_same_clock alone lets a
# zero-logic group (e.g. a free-running counter wc feeding per-slot epoch flops behind per-slot ICGs) be re-hung
# from one gated leaf onto another gated or ungated leaf -- a functional change (S81 CRS4 10-29: 44 epo flops,
# post-route LEC NOT EQUIVALENT).  A sink moves only between leaves with the same gating identity.
global la_groot_c
set la_groot_c [dict create]
proc la_groot {net} {
  global la_groot_c
  set n0 [$net getName]
  if {[dict exists $la_groot_c $n0]} { return [dict get $la_groot_c $n0] }
  set par 0; set key ""
  for {set i 0} {$i < 64} {incr i} {
    set drv [la_drv $net]
    if {$drv eq ""} { set key "port:[$net getName]"; break }
    if {![la_is_bufinv $drv]} { set key "inst:[$drv getName]"; break }
    if {[regexp {INV} [[$drv getMaster] getName]]} { set par [expr {1 - $par}] }
    set in ""
    foreach it [$drv getITerms] { if {[$it isInputSignal] && [$it getNet] ne "NULL"} { set in [$it getNet]; break } }
    if {$in eq ""} { set key "undriven:[$drv getName]"; break }
    set net $in
  }
  if {$key eq ""} { set key "deep:[$net getName]" }
  set key "$key:$par"
  dict set la_groot_c $n0 $key
  return $key
}

# union-find over zero-logic pairs
array set la_par {}
proc la_find {x} { global la_par; while {$la_par($x) ne $x} { set la_par($x) $la_par($la_par($x)); set x $la_par($x) }; return $x }
proc la_union {a b} { global la_par; set ra [la_find $a]; set rb [la_find $b]; if {$ra ne $rb} { set la_par($ra) $rb } }
set la_pairs 0; set la_cross0 0
set la_pairlist {}
dict for {name it} $la_ck {
  set inst [$it getInst]
  foreach s [lsort -unique [la_succ $inst $la_depth]] {
    if {$s eq $name} continue
    incr la_pairs
    lappend la_pairlist [list $name $s]
    foreach x [list $name $s] { if {![info exists la_par($x)]} { set la_par($x) $x } }
    la_union $name $s
    if {[la_leaf $name] ne [la_leaf $s]} { incr la_cross0 }
  }
}
# leaf fanout now
set la_fo [dict create]
set la_fomax 0
dict for {name it} $la_ck {
  set n [$it getNet]
  if {$n eq "NULL"} continue
  dict incr la_fo [$n getName]
  set f [dict get $la_fo [$n getName]]
  if {$f > $la_fomax} { set la_fomax $f }
}
set la_cap [expr {$la_fomax + $la_slack}]
set la_groups [dict create]
foreach x [array names la_par] { dict lappend la_groups [la_find $x] $x }
set la_moved 0; set la_gmoved 0; set la_skip_big 0; set la_skip_far 0; set la_skip_cap 0; set la_skip_drv 0; set la_skip_clock 0; set la_skip_gate 0; set la_ok 0
# One group (or local sub-group) -> one leaf.  Returns moved | ok | clock | big | driver | far | gate | cap.
# Unchanged rule set; DIE-S81-85 11-09 only moved it into a proc so the local split pass below applies the same checks.
proc la_try {mem} {
  global la_ck la_fo la_cap la_ronly la_moved la_blk la_um la_dbu la_maxg
  if {![la_same_clock $mem]} { return clock }
  if {[llength $mem] > $la_maxg} { return big }
  # candidate leaves: by member count, ties -> nearest centroid
  set cnt [dict create]
  foreach m $mem { set n [la_leaf $m]; if {$n ne "NULL"} { dict incr cnt [$n getName] } }
  if {[dict size $cnt] <= 1} { return ok }
  set best ""; set bestc -1
  dict for {nn c} $cnt { if {$c > $bestc} { set best $nn; set bestc $c } }
  set net [$la_blk findNet $best]
  set drv [la_drv $net]
  if {$drv eq "" || [$net getSigType] ne "CLOCK"} { return driver }
  # la_same_clock above established one unambiguous timing clock for this group.
  lassign [la_xy $drv] dx dy
  set mv {}
  foreach m $mem {
    set it [dict get $la_ck $m]
    if {[[$it getNet] getName] eq $best} continue
    lassign [la_xy [$it getInst]] x y
    if {(abs($x - $dx) + abs($y - $dy)) > $la_um * $la_dbu} { return far }
    lappend mv $it
  }
  set la_g0 [la_groot $net]
  foreach it $mv { if {[la_groot [$it getNet]] ne $la_g0} { return gate } }
  if {[dict get $la_fo $best] + [llength $mv] > $la_cap} { return cap }
  if {!$la_ronly} {
    foreach it $mv {
      set old [$it getNet]
      dict incr la_fo [$old getName] -1
      $it disconnect
      $it connect $net
      dict incr la_fo $best
      incr la_moved
    }
  }
  return moved
}
set la_redo [dict create]
dict for {r mem} $la_groups {
  switch -- [la_try $mem] {
    moved { incr la_gmoved }
    ok { incr la_ok }
    clock { incr la_skip_clock }
    big { incr la_skip_big; dict set la_redo $r 1 }
    driver { incr la_skip_drv }
    far { incr la_skip_far; dict set la_redo $r 1 }
    gate { incr la_skip_gate }
    cap { incr la_skip_cap }
  }
}
set la_cross1 0
foreach pr $la_pairlist { lassign $pr a b; if {[la_leaf $a] ne [la_leaf $b]} { incr la_cross1 } }
puts "OT_LEAF_AFF pairs $la_pairs groups [dict size $la_groups] cross_leaf_before $la_cross0 cross_leaf_after $la_cross1 groups_moved $la_gmoved sinks_moved $la_moved same_leaf_already $la_ok skip_big $la_skip_big skip_far $la_skip_far skip_cap $la_skip_cap skip_driver $la_skip_drv skip_clock $la_skip_clock skip_gate $la_skip_gate leaf_cap $la_cap radius_um $la_um report_only $la_ronly"
# ---- DIE-S81-85 11-09 LOCAL SPLIT (OT_LEAF_AFF_SPLIT_UM, default 30 um; 0 = off; the OT_LEAF_AFF line above is unchanged) ----
# A zero-logic group that spans the core (TX vD: every pin_q[0..2] -> d0 -> ... -> d6 bit chain, 10 flops from the
# input face to the output mux) failed skip_far as a whole, so all 514 groups stayed on CTS leaves and 3061 of 4617
# zero-logic pairs crossed leaves; the 111 routed FF hold misses are such pairs 1.4-5 um apart on neighbouring leaves
# 6-8 um apart with 13-22 ps insertion skew (data QN -> INV -> D = 47 ps vs 25 unc + 12 hold).  Each skipped group is
# cut into LOCAL sub-groups: its pairs are merged nearest-first (Kruskal on flop distance) while the merged flop
# bounding box half-perimeter stays <= OT_LEAF_AFF_SPLIT_UM and the size <= OT_LEAF_AFF_MAX_GROUP; each sub-group then
# goes through the same la_try checks (one clock, gating identity, radius, leaf cap).  Pairs cut between sub-groups
# stay as CTS built them (no worse than before).  Routed S81 TX: core FF hold 111 ep / -6.12 (110 cross-leaf) in tx_vD
# -> 20 ep / -2.85 (10 cross-leaf) in tx_vS4 with the default leaf cap (+4).  Do NOT raise OT_LEAF_AFF_SLACK with it:
# tx_vS at +8 moved the skew into fat leaves (capture CK ~11 ps behind the leaf output on 25-37 sink leaves).
set la_split_um [la_env OT_LEAF_AFF_SPLIT_UM 30]
if {$la_split_um > 0 && [dict size $la_redo]} {
  set la_s_gp [dict create]
  foreach pr $la_pairlist {
    lassign $pr a b
    set r [la_find $a]
    if {[dict exists $la_redo $r]} { dict lappend la_s_gp $r $pr }
  }
  set la_s_lim [expr {$la_split_um * $la_dbu}]
  set la_s_n 0; set la_s_moved 0; set la_s_stat [dict create]
  dict for {r prs} $la_s_gp {
    array unset la_sp; array unset la_sbb; array unset la_ssz
    set es {}
    foreach pr $prs {
      lassign $pr a b
      foreach x [list $a $b] {
        if {![info exists la_sp($x)]} {
          set la_sp($x) $x; set la_ssz($x) 1
          lassign [la_xy [[dict get $la_ck $x] getInst]] x0 y0
          set la_sbb($x) [list $x0 $y0 $x0 $y0]
        }
      }
      lassign $la_sbb($a) ax ay; lassign $la_sbb($b) bx by
      lappend es [list [expr {abs($ax - $bx) + abs($ay - $by)}] $a $b]
    }
    foreach e [lsort -integer -index 0 $es] {
      lassign $e d a b
      set ra $a; while {$la_sp($ra) ne $ra} { set ra $la_sp($ra) }
      set rb $b; while {$la_sp($rb) ne $rb} { set rb $la_sp($rb) }
      if {$ra eq $rb} continue
      lassign $la_sbb($ra) a0 a1 a2 a3; lassign $la_sbb($rb) b0 b1 b2 b3
      set m0 [expr {min($a0, $b0)}]; set m1 [expr {min($a1, $b1)}]; set m2 [expr {max($a2, $b2)}]; set m3 [expr {max($a3, $b3)}]
      if {($m2 - $m0) + ($m3 - $m1) > $la_s_lim} continue
      if {$la_ssz($ra) + $la_ssz($rb) > $la_maxg} continue
      set la_sp($ra) $rb; set la_sbb($rb) [list $m0 $m1 $m2 $m3]; set la_ssz($rb) [expr {$la_ssz($ra) + $la_ssz($rb)}]
    }
    set subs [dict create]
    foreach x [array names la_sp] {
      set rx $x; while {$la_sp($rx) ne $rx} { set rx $la_sp($rx) }
      dict lappend subs $rx $x
    }
    dict for {rx mem} $subs {
      if {[llength $mem] < 2} continue
      incr la_s_n
      set st [la_try $mem]
      dict incr la_s_stat $st
      if {$st eq "moved"} { incr la_s_moved }
    }
  }
  set la_cross2 0
  foreach pr $la_pairlist { lassign $pr a b; if {[la_leaf $a] ne [la_leaf $b]} { incr la_cross2 } }
  puts "OT_LEAF_AFF_SPLIT span_um $la_split_um groups [dict size $la_redo] subgroups $la_s_n moved $la_s_moved status {$la_s_stat} sinks_moved_total $la_moved cross_leaf_after $la_cross2 leaf_cap $la_cap report_only $la_ronly"
}
if {$la_moved > 0} { estimate_parasitics -placement }
