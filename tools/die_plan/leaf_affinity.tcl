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
# Prints OT_LEAF_AFF ... summary lines (pairs, cross-leaf before / after, groups moved / skipped by reason).
# The ORFS POST_CTS hook may be sourced inside a procedure. Helper procs
# share these dictionaries/union-find arrays through the global namespace.
global la_d la_ck la_par la_clock
proc la_env {k d} { expr {[info exists ::env($k)] && $::env($k) ne "" ? $::env($k) : $d} }
set la_um [la_env OT_LEAF_AFF_UM 30.0]
set la_maxg [la_env OT_LEAF_AFF_MAX_GROUP 24]
set la_slack [la_env OT_LEAF_AFF_SLACK 4]
set la_depth [la_env OT_LEAF_AFF_DEPTH 4]
set la_ronly [la_env OT_LEAF_AFF_REPORT_ONLY 0]
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
  dict unset la_d [$it getInst]:[[$it getMTerm] getName]
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
set la_moved 0; set la_gmoved 0; set la_skip_big 0; set la_skip_far 0; set la_skip_cap 0; set la_skip_drv 0; set la_skip_clock 0; set la_ok 0
dict for {r mem} $la_groups {
  if {![la_same_clock $mem]} { incr la_skip_clock; continue }
  if {[llength $mem] > $la_maxg} { incr la_skip_big; continue }
  # candidate leaves: by member count, ties -> nearest centroid
  set cnt [dict create]
  foreach m $mem { set n [la_leaf $m]; if {$n ne "NULL"} { dict incr cnt [$n getName] } }
  if {[dict size $cnt] <= 1} { incr la_ok; continue }
  set best ""; set bestc -1
  dict for {nn c} $cnt { if {$c > $bestc} { set best $nn; set bestc $c } }
  set net [$la_blk findNet $best]
  set drv [la_drv $net]
  if {$drv eq "" || [$net getSigType] ne "CLOCK"} { incr la_skip_drv; continue }
  # la_same_clock above established one unambiguous timing clock for this group.
  lassign [la_xy $drv] dx dy
  set mv {}; set far 0
  foreach m $mem {
    set it [dict get $la_ck $m]
    if {[[$it getNet] getName] eq $best} continue
    lassign [la_xy [$it getInst]] x y
    if {(abs($x - $dx) + abs($y - $dy)) > $la_um * $la_dbu} { set far 1; break }
    lappend mv $it
  }
  if {$far} { incr la_skip_far; continue }
  if {[dict get $la_fo $best] + [llength $mv] > $la_cap} { incr la_skip_cap; continue }
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
  incr la_gmoved
}
set la_cross1 0
foreach pr $la_pairlist { lassign $pr a b; if {[la_leaf $a] ne [la_leaf $b]} { incr la_cross1 } }
puts "OT_LEAF_AFF pairs $la_pairs groups [dict size $la_groups] cross_leaf_before $la_cross0 cross_leaf_after $la_cross1 groups_moved $la_gmoved sinks_moved $la_moved same_leaf_already $la_ok skip_big $la_skip_big skip_far $la_skip_far skip_cap $la_skip_cap skip_driver $la_skip_drv skip_clock $la_skip_clock leaf_cap $la_cap radius_um $la_um report_only $la_ronly"
if {$la_moved > 0} { estimate_parasitics -placement }
