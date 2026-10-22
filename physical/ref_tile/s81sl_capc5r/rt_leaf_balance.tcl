# DRIVE-S81-CAP 10-20: REGION LATENCY BALANCE inside each clock region of the landed capc parent.
# Evidence (capc5e 4_1_cts.odb, per-sink TT arrival, placement RC): the single TritonCTS tree of region rt (ck_rt, W-face
# entry) gives
#   N band (rt readers + rt->rn writer banks, y 164..209)  382..426 ps
#   S band (rt->rs writer banks, y 15..39, under u_rt)     444..497 ps
#   u_rt boundary flops (clk pin 161 + R 234..298)         395..459 ps
# i.e. each band is tight (44 / 53 ps) but the H-tree branch that goes around the 259-um u_rt to the S band is ~62 ps
# late: a systematic branch imbalance, not a spread problem (gate: TT 102 / FF 84 > 80).
# Fix = classic post-CTS latency balancing on the region's own tree: every LEAF driver (a buffer whose loads are only
# sequential clock pins / CTS dummy loads) is one group, every hard child's clock pin is one group (centre = pin arrival
# + the child's boundary-insertion centre from its closed insertion.json); each group's centre is brought up to the
# latest group centre of the region (fixed before balancing) by whole delay-buffer stages inserted in front of the
# group's driver (child: in front of its clock pin, one measured stage per round).  Same ports, clocks, regions, flops,
# landings and cycles; only clock-tree buffering is added.  Cells are named delaybuf_otrtb_* (clk_net_protect keeps
# them); offline replay on the capc5e CTS db: rt soft 382..497 / pair 102 -> soft 475..499 / pair 50 ps (427 BUFx4).
# Wrapped in catch: a failure leaves the CTS result untouched.
# ::ot_rtb_regions: list of {clock {{child_clock_pin centre_ps half_span_ps} ...}}  (TT refs, clock_entry.sdc ot_ce_refs)
if {![info exists ::ot_rtb_regions]} { set ::ot_rtb_regions {{ot_entry_0 {{u_rt/clk 266.15 31.85}}}} }
set ::ot_rtb_cell BUFx4_ASAP7_75t_R
set ::ot_rtb_tol 6.0
set ::ot_rtb_stage 22.0   ;# ~TT delay of one BUFx4 stage in front of a leaf buffer (offline replay)
set ::ot_rtb_max 12
if {![info exists ::ot_rtb_n]} { set ::ot_rtb_n 0 }

proc ot_rtb_arr {p} {
  set a [get_property $p arrival_max_rise]
  if {$a eq "" || $a eq "INF" || $a eq "-INF"} { return "" }
  if {$a < 1.0} { set a [expr {$a * 1e12}] }
  return $a
}

proc ot_rtb_leaf_ok {di} {
  # every load of the driver's output is a sequential standard cell or a CTS dummy load
  foreach it [$di getITerms] {
    if {![$it isOutputSignal]} continue
    set n [$it getNet]
    if {$n eq "NULL"} { return 0 }
    foreach l [$n getITerms] {
      if {![$l isInputSignal]} continue
      set li [$l getInst]
      if {[string match "clkload*" [$li getName]]} continue
      set m [$li getMaster]
      if {[$m isBlock] || ![$m isSequential]} { return 0 }
    }
  }
  return 1
}

# leaf groups of one clock: driver inst name -> sta pins (soft sequential clock pins only)
proc ot_rtb_groups {clock} {
  set blk [ord::get_db_block]
  set g [dict create]; set skipped 0
  foreach p [all_registers -clock $clock -clock_pins] {
    set it [sta::sta_to_db_pin $p]
    if {$it eq "NULL" || $it eq ""} continue
    if {[[[$it getInst] getMaster] isBlock]} continue
    set drv [[$it getNet] getFirstOutput]
    if {$drv eq "NULL" || $drv eq ""} continue
    dict lappend g [[$drv getInst] getName] $p
  }
  set keep [dict create]
  dict for {d pins} $g {
    set di [$blk findInst $d]
    if {$di eq "NULL" || [[$di getMaster] isBlock] || ![ot_rtb_leaf_ok $di]} { incr skipped; continue }
    dict set keep $d $pins
  }
  return [list $keep $skipped]
}

# insert one delay buffer in front of ITerm $sink (its current net feeds the new buffer; the buffer drives $sink)
proc ot_rtb_insert {sink x y} {
  set blk [ord::get_db_block]
  set n0 [$sink getNet]
  set inst [$sink getInst]
  set dt_n [$n0 isDoNotTouch]; set dt_i [$inst isDoNotTouch]
  $n0 setDoNotTouch 0; $inst setDoNotTouch 0
  set m [[ord::get_db] findMaster $::ot_rtb_cell]
  set k [incr ::ot_rtb_n]
  set b [odb::dbInst_create $blk $m delaybuf_otrtb_$k]
  $b setLocation $x $y; $b setPlacementStatus PLACED
  set n1 [odb::dbNet_create $blk otrtb_net_$k]; $n1 setSigType CLOCK
  $sink disconnect
  [$b findITerm A] connect $n0
  [$b findITerm Y] connect $n1
  $sink connect $n1
  $n0 setDoNotTouch $dt_n; $inst setDoNotTouch $dt_i
  return $b
}

proc ot_rtb_measure {groups children} {
  set res [dict create]
  dict for {d pins} $groups {
    set lo 1e9; set hi -1e9; set c 0
    foreach p $pins {
      set a [ot_rtb_arr $p]
      if {$a eq ""} continue
      incr c; if {$a < $lo} { set lo $a }; if {$a > $hi} { set hi $a }
    }
    if {$c} { dict set res $d [list [expr {($lo + $hi) / 2.0}] $lo $hi] }
  }
  foreach ch $children {
    lassign $ch pin rc half
    set a [ot_rtb_arr [get_pins $pin]]
    if {$a ne ""} { set c [expr {$a + $rc}]; dict set res child:$pin [list $c [expr {$c - $half}] [expr {$c + $half}]] }
  }
  return $res
}

proc ot_rtb_span {res} {
  set lo 1e9; set hi -1e9; set out ""
  dict for {k v} $res { if {[string match child:* $k]} continue; lassign $v c l h; if {$l < $lo} { set lo $l }; if {$h > $hi} { set hi $h } }
  append out [format "soft %.1f..%.1f (%.1f)" $lo $hi [expr {$hi - $lo}]]
  dict for {k v} $res {
    if {![string match child:* $k]} continue
    lassign $v c cl ch
    append out [format " %s %.1f..%.1f pair %.1f" [string range $k 6 end] $cl $ch [expr {max($hi - $cl, $ch - $lo)}]]
  }
  return $out
}

proc ot_rtb_balance_region {clock children} {
  set blk [ord::get_db_block]
  lassign [ot_rtb_groups $clock] keep skipped
  estimate_parasitics -placement
  set res [ot_rtb_measure $keep $children]
  puts "OT_RTB $clock before: [dict size $keep] leaf groups ($skipped not leaf-only), [ot_rtb_span $res]"
  # fixed target = the latest group centre BEFORE balancing (never chased upward)
  set t -1e9
  dict for {k v} $res { if {[lindex $v 0] > $t} { set t [lindex $v 0] } }
  set n0 $::ot_rtb_n
  for {set r 0} {$r < $::ot_rtb_max} {incr r} {
    set moved 0
    dict for {k v} $res {
      set gap [expr {$t - [lindex $v 0]}]
      set ns [expr {int(floor($gap / $::ot_rtb_stage))}]
      if {$gap <= $::ot_rtb_tol || $ns < 1} continue
      if {[string match child:* $k]} {
        set ns 1
        set sink [$blk findITerm [string range $k 6 end]]
        if {$sink eq "NULL"} continue
        set bb [[$sink getInst] getBBox]; set ib [$sink getBBox]
        set x [expr {([$ib xMin] + [$ib xMax]) / 2}]
        set y [expr {abs([$ib yMax] - [$bb yMax]) < abs([$ib yMin] - [$bb yMin]) ? [$bb yMax] + 2000 : [$bb yMin] - 4000}]
      } else {
        set di [$blk findInst $k]
        set sink [$di findITerm A]
        if {$sink eq "NULL"} continue
        lassign [$di getLocation] x y
      }
      for {set j 0} {$j < $ns} {incr j} { ot_rtb_insert $sink $x $y; incr moved }
    }
    if {!$moved} break
    if {[llength [info procs ot_pg_standard_bind]]} { ot_pg_standard_bind rt_leaf_balance } else { global_connect }
    estimate_parasitics -placement
    set res [ot_rtb_measure $keep $children]
    puts "OT_RTB $clock round $r: +$moved delay buffers, [ot_rtb_span $res]"
  }
  puts "OT_RTB $clock done: [expr {$::ot_rtb_n - $n0}] delay buffers ($::ot_rtb_cell), [ot_rtb_span $res]"
}

proc ot_rtb_balance {} {
  set_propagated_clock [all_clocks]
  foreach reg $::ot_rtb_regions {
    lassign $reg clock children
    if {[catch {ot_rtb_balance_region $clock $children} e]} { puts "OT_RTB ERROR $clock (left as built): $e" }
  }
}

# ---- post-CTS REFINE (run from post_cts.tcl, after DPL + hold repair, before write_db; the gate measures this db).
# capc5i/j gate: after the in-CTS balance, DPL + repair moved the region (rt soft 512..536 -> 470..497) while the u_rt
# chain did not follow (u_rt 493..556: pair 86).  Here each hard child's centre is brought to its region's soft centre:
# delay stages the in-CTS pass put in front of the child pin are REMOVED when the child is late, stages are ADDED when
# it is early; then legalise and re-measure (the same measurement the gate makes: offline replay matched it to 0.1 ps).
proc ot_rtb_soft_centre {res} {
  set lo 1e9; set hi -1e9
  dict for {k v} $res { if {[string match child:* $k]} continue; lassign $v c l h; if {$l < $lo} { set lo $l }; if {$h > $hi} { set hi $h } }
  return [expr {($lo + $hi) / 2.0}]
}
proc ot_rtb_remove_stage {sink} {
  # sink's driver must be one of our delay buffers; reconnect sink to that buffer's input net and delete it
  set blk [ord::get_db_block]
  set n1 [$sink getNet]
  set d [$n1 getFirstOutput]
  if {$d eq "NULL" || $d eq ""} { return 0 }
  set b [$d getInst]
  if {![string match "delaybuf_otrtb_*" [$b getName]]} { return 0 }
  if {[llength [$n1 getITerms]] != 2} { return 0 }
  set n0 [[$b findITerm A] getNet]
  set inst [$sink getInst]
  set dt_i [$inst isDoNotTouch]; set dt_n0 [$n0 isDoNotTouch]
  $inst setDoNotTouch 0; $n0 setDoNotTouch 0; $b setDoNotTouch 0; $n1 setDoNotTouch 0
  $sink disconnect
  odb::dbInst_destroy $b
  odb::dbNet_destroy $n1
  $sink connect $n0
  $inst setDoNotTouch $dt_i; $n0 setDoNotTouch $dt_n0
  return 1
}
proc ot_rtb_refine {} {
  set blk [ord::get_db_block]
  set_propagated_clock [all_clocks]
  foreach reg $::ot_rtb_regions {
    lassign $reg clock children
    if {![llength $children]} continue
    lassign [ot_rtb_groups $clock] keep skipped
    for {set r 0} {$r < 6} {incr r} {
      estimate_parasitics -placement
      set res [ot_rtb_measure $keep $children]
      set sc [ot_rtb_soft_centre $res]
      puts "OT_RTB_REFINE $clock round $r: [ot_rtb_span $res] (soft centre [format %.1f $sc])"
      set moved 0
      foreach ch $children {
        set pin [lindex $ch 0]
        if {![dict exists $res child:$pin]} continue
        set err [expr {[lindex [dict get $res child:$pin] 0] - $sc}]
        set sink [$blk findITerm $pin]
        if {$err > 12.0} {
          incr moved [ot_rtb_remove_stage $sink]
        } elseif {$err < -16.0} {
          set ib [$sink getBBox]; set bb [[$sink getInst] getBBox]
          set x [expr {([$ib xMin] + [$ib xMax]) / 2}]
          set y [expr {abs([$ib yMax] - [$bb yMax]) < abs([$ib yMin] - [$bb yMin]) ? [$bb yMax] + 8000 : [$bb yMin] - 8000}]
          set nb [ot_rtb_insert $sink $x $y]; $nb setDoNotTouch 1; incr moved
        }
      }
      if {!$moved} break
      if {[llength [info procs ot_pg_standard_bind]]} { ot_pg_standard_bind rt_leaf_refine } else { global_connect }
      detailed_placement
    }
  }
}

if {![info exists ::ot_rtb_offline]} {
  rename clock_tree_synthesis ::ot_rtb_cts_orig
  proc clock_tree_synthesis {args} {
    ::ot_rtb_cts_orig {*}$args
    if {[catch {ot_rtb_balance} e]} { puts "OT_RTB ERROR (CTS result kept): $e" }
  }
}
