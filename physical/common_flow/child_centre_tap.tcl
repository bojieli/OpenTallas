# child_centre_tap.tcl (HBM-ELEM13/SU-PSLICE14 2026-10-21): post-CTS clock-pin delay tap that CENTRES each hard child's
# boundary-flop insertion range on its region root's soft-register range, for LANDED multiple_cts_roots clusters
# (tools/ref_tile spec "child_centre_tap"; same mechanism as landed_raw_tap.tcl, coordinator option A for h16c).
#
# Why (pslice_c5 lp13a/b, ep9 4_1_cts, Codex reconstruction 81f05c5e0): TritonCTS splits every region root into a macro
# net (the hard child's clock pin) and a register net, and balances the register tree to (macro pin arrival + the
# child's Liberty max_clock_tree_path), i.e. to the child's LATEST boundary flop (insertion.json boundary MAX).  The soft
# registers then sit at the child's max +- their own spread, so the per-root child/soft pair span the gate judges
# (clock_rule, <= 80 ps TT and FF) is the child's whole internal range PLUS half the soft spread: pgcol_l range 62.6 ps TT
# -> L roots 88-94 ps (lp13a), pghead 23 ps + a 47-ps 3,412-sink soft cluster -> ck_h 87.8 ps; pgcol_s (range 36) passed.
# No CTS option moves that target (it is read from the child's closed ETM, which is never edited).  This hook, run right
# after clock_tree_synthesis, measures per root the soft register clock arrivals (min..max) and the hard child's clock-pin
# arrival a, and inserts a dont-touch chain of clock buffers in front of the child's clock pin until
#     a + (cmin + cmax) / 2  >=  (smin + smax) / 2        (child range centre on the soft range centre)
# so the pair span becomes ~ (child range + soft range) / 2.  The tap only ever DELAYS the child pin (the soft tree is
# always at or after the child centre, by the CTS target above); a root whose child is already centred gets no buffer.
# Nothing else changes: no SDC latency, no ETM edit, no other net; the gate's clock_rule still judges the real arrivals.
#
# Input (ref_tile pre_cts.tcl): ::ot_cct_children = dict {<child instance>} {tt {min max} ff {min max} ss {min max}}
# (views/<child>/insertion.json <corner>.boundary min / max).  Env OT_CCT_BUF (default BUFx4_ASAP7_75t_R), OT_CCT_MAX
# (default 24 buffers per pin), OT_CCT_TOL (default 4 ps: no tap for a smaller centring error).  Fails closed when a child,
# its unique clock pin / clock, its arrival or its soft registers are missing.
if {![llength [info procs ot_pg_standard_bind]]} {
  # PG binding before protection (ROOT4 10-19), as landed_raw_tap.tcl: the helper is sourced when no hook loaded it yet
  set ot_cct_pg_helper [file join [file dirname [info script]] native_pg_binding.tcl]
  if {[info exists ::env(OT_PG_HELPER)]} {set ot_cct_pg_helper $::env(OT_PG_HELPER)} elseif {![file exists $ot_cct_pg_helper]} {set ot_cct_pg_helper /src/physical/common_flow/native_pg_binding.tcl}
  source $ot_cct_pg_helper
}
# HBMb/IDXSU-PS15 2026-10-21 (r15): two defects of the r14 form, both seen in pslice lp14a (pve1 cts.log):
#  (1) the corner came from the scene NAME, but the gate's setup scene is named WC while it holds the TT liberties
#      (OT_ORFS_CORNER_OVERRIDE=TC): "OT_CCT ss u_h/clk ... child 319.1+(134.2..156.8)" = pghead SS ranges on TT arrivals.
#      Now a WC/SS-named scene is TT when the hard child's loaded Liberty set has a _tt and no _ss library.
#  (2) centring at ONE corner: lp13a L roots are +20..32 ps late at TT but within +-7 at FF, so a TT-centred tap pushes FF to
#      the limit and a BUFx4 step (~29 ps) overshoots (r14 offline: L FF 82-91).  Now the tap minimises the WORST pair over
#      every scene with propagated clock arrivals (setup scene + BC when BC has them), greedily, with a step ladder
#      (OT_CCT_BUFS, default BUFx4 -> BUFx2 -> HB1xp67): a step is kept only when it lowers that worst pair by >= 0.5 ps,
#      else it is removed and the next smaller master is tried.  One scene only = the r14 centring (minimum pair).
proc ot_cct_arr {pin {scene ""}} {
  # propagated-clock arrival at a clock pin in one scene (same tag read as landed_raw_tap ot_lrt_wire): rising, else falling
  sta::worst_slack_cmd max
  if {$scene eq ""} { set scene [get_property [sta::cmd_scene] name] }
  set best {}
  foreach transition {rise fall} marker {^ v} {
    foreach vertex [$pin vertices] {
      if {$vertex eq "NULL"} continue
      set paths [$vertex path_iterator $transition max]
      while {[$paths has_next]} {
        set path [$paths next]
        set tag [$path tag]
        if {[lindex $tag 1] ne $scene || [lindex $tag 2] ne "${marker}max" || [string first "(clock prop)" $tag] < 0} continue
        set a [sta::time_sta_ui [$path arrival]]
        if {[string is double -strict $a] && ![regexp -nocase {inf|nan} $a] && ($best eq "" || $a > $best)} { set best $a }
      }
      $paths finish
    }
    if {$best ne ""} break
  }
  return $best
}
proc ot_cct_scenes {pin} {
  # every scene with a propagated clock arrival at this pin (command scene first)
  sta::worst_slack_cmd max
  set cmd [get_property [sta::cmd_scene] name]
  set out [list $cmd]
  foreach transition {rise fall} {
    foreach vertex [$pin vertices] {
      if {$vertex eq "NULL"} continue
      set paths [$vertex path_iterator $transition max]
      while {[$paths has_next]} {
        set tag [[$paths next] tag]
        if {[string first "(clock prop)" $tag] < 0} continue
        set s [lindex $tag 1]
        if {[lsearch -exact $out $s] < 0} { lappend out $s }
      }
      $paths finish
    }
  }
  return $out
}
proc ot_cct_corner {cell {scene ""}} {
  # the Liberty corner of a scene's arrivals.  BC / FF / TT / TC names are taken as named; a WC / SS-named setup scene is
  # TT when the hard child's loaded Liberty set has a _tt and no _ss library (OT_ORFS_CORNER_OVERRIDE=TC gate sessions),
  # SS when it has an _ss one; any other name (single-scene session) = the corner of the loaded libraries
  if {$scene eq ""} { set scene [get_property [sta::cmd_scene] name] }
  set sc [string tolower $scene]
  if {[regexp {^(bc|ff|fast|min)} $sc]} { return ff }
  if {[regexp {^(tt|tc|typ)} $sc]} { return tt }
  set have {}
  foreach lc [get_lib_cells -quiet -of_objects $cell] {
    if {[regexp -nocase {_(tt|ff|ss)(?:[/_.]|$)} [get_full_name $lc] -> c]} { dict set have [string tolower $c] 1 }
  }
  # Child-associated libraries take precedence.  An unrelated loaded _ss library must not
  # turn the gate's WC (TT) child arrivals into SS ranges.  Fall back to global names
  # only when this child's Liberty cells carry no recognizable corner suffix.
  if {![dict size $have]} {
    foreach lib [get_libs -quiet *] {
      if {[regexp -nocase {_(tt|ff|ss)(?:_|$)} [get_full_name $lib] -> c]} { dict set have [string tolower $c] 1 }
    }
  }
  if {[regexp {^(wc|ss|slow|max)} $sc]} {
    if {[dict exists $have ss]} { return ss }
    if {[dict exists $have tt]} { return tt }
    error "OT_CCT: setup scene $scene has neither a _tt nor an _ss library"
  }
  set ks [dict keys $have]
  if {[llength $ks] == 1} { return [lindex $ks 0] }
  if {[dict exists $have tt] && ![dict exists $have ss]} { return tt }
  error "OT_CCT: no unique corner for scene $scene (libraries: $ks)"
}
proc ot_cct_worst {r} {
  # worst child/soft pair over the record's scenes at the current pin arrivals (dict scene -> d)
  set w ""
  dict for {s v} [dict get $r sc] {
    lassign $v corner cmin cmax smin smax
    set d [dict get $r d $s]
    set p [expr {max($d + $cmax - $smin, $smax - $d - $cmin)}]
    if {$w eq "" || $p > $w} { set w $p }
  }
  return $w
}
proc ot_cct_measure {r} {
  dict for {s v} [dict get $r sc] {
    set a [ot_cct_arr [dict get $r pin] $s]
    if {$a eq ""} { error "OT_CCT: [dict get $r iname] lost its clock arrival in scene $s" }
    dict set r d $s $a
  }
  return $r
}
proc ot_cct_insert {block bm ain aout r} {
  # one dont-touch-ready buffer of master bm between the child clock pin and its current net; returns the record
  dict with r {
    set old [$it getNet]
    set b [odb::dbInst_create $block $bm "ot_cct_${iname}_${mterm}_$n"]
    if {$b eq "NULL"} { error "OT_CCT: cannot create tap buffer" }
    $b setLocation [expr {int($x)}] [expr {int($y)}]
    $b setPlacementStatus PLACED
    set nn [odb::dbNet_create $block "ot_cct_n_${iname}_${mterm}_$n"]
    $nn setSigType CLOCK
    # a protected clock net (clk_net_protect.tcl dont_touch) is opened for this one reconnect and re-protected;
    # the new tap net inherits the protection
    set dt [$old isDoNotTouch]
    if {$dt} { $old setDoNotTouch 0 }
    $it disconnect
    [$b findITerm $ain] connect $old
    [$b findITerm $aout] connect $nn
    $it connect $nn
    if {$dt} { $old setDoNotTouch 1; $nn setDoNotTouch 1 }
    if {[info exists ::env(OT_PG_STRICT)] && $::env(OT_PG_STRICT) eq "1"} {ot_pg_bind_before_protect [ot_pg_prepare_targets $block [list $b]] $b}
    set last [list $b $nn $old]
    lappend made $b $nn
    incr n
  }
  return $r
}
proc ot_cct_remove_last {r} {
  dict with r {
    lassign $last b nn old
    set made [lrange $made 0 end-2]
    set dt [$old isDoNotTouch]
    if {$dt} { $old setDoNotTouch 0 }
    $nn setDoNotTouch 0
    $it disconnect
    odb::dbInst_destroy $b
    odb::dbNet_destroy $nn
    $it connect $old
    if {$dt} { $old setDoNotTouch 1 }
    incr n -1
    set last {}
  }
  return $r
}
# Propagation is per constraint mode.  A WC-only set_propagated_clock leaves the
# production BC mode ideal, so its tags disappear from the minimax objective.
# Temporarily propagate only ideal clocks in every loaded mode and restore them.
proc ot_cct_propagate_modes {} {
  set original [sta::cmd_mode_name]
  set changed {}
  foreach mode [get_modes *] {
    set name [get_property $mode name]
    set_mode $name
    set ideal {}
    foreach c [all_clocks] { if {![get_property $c is_propagated]} { lappend ideal $c } }
    if {[llength $ideal]} {
      set_propagated_clock $ideal
      dict set changed $name $ideal
    }
  }
  set_mode $original
  return $changed
}
proc ot_cct_restore_modes {changed} {
  set original [sta::cmd_mode_name]
  dict for {mode clocks} $changed {
    set_mode $mode
    unset_propagated_clock $clocks
  }
  set_mode $original
}
proc ot_cct_tap {} {
  if {![info exists ::ot_cct_children] || ![dict size $::ot_cct_children]} return
  if {[info exists ::env(OT_PG_STRICT)] && $::env(OT_PG_STRICT) eq "1"} {ot_pg_require_cts_placement_or_empty_context}
  set block [ord::get_db_block]
  set lim [expr {[info exists ::env(OT_CCT_MAX)] ? $::env(OT_CCT_MAX) : 24}]
  set gain [expr {[info exists ::env(OT_CCT_GAIN)] ? $::env(OT_CCT_GAIN) : 0.5}]
  # step ladder (OT_CCT_BUF = r14 single master, still honoured as the first rung)
  set names [expr {[info exists ::env(OT_CCT_BUFS)] ? $::env(OT_CCT_BUFS) : "BUFx4_ASAP7_75t_R BUFx2_ASAP7_75t_R HB1xp67_ASAP7_75t_R"}]
  if {[info exists ::env(OT_CCT_BUF)]} { set names [linsert $names 0 $::env(OT_CCT_BUF)] }
  set ladder {}
  foreach nm $names {
    set bm [[ord::get_db] findMaster $nm]
    if {$bm eq "NULL"} { error "OT_CCT: buffer master $nm missing" }
    set ain ""; set aout ""
    foreach mt [$bm getMTerms] {
      if {[$mt getSigType] in {POWER GROUND}} continue
      if {[$mt getIoType] eq "INPUT"} { set ain [$mt getName] } elseif {[$mt getIoType] eq "OUTPUT"} { set aout [$mt getName] }
    }
    lappend ladder [list $nm $bm $ain $aout]
  }
  set propagation_changes [ot_cct_propagate_modes]
  estimate_parasitics -placement
  set recs {}
  dict for {iname ranges} $::ot_cct_children {
    set inst [$block findInst $iname]
    if {$inst eq "NULL"} {
      foreach i [$block getInsts] { if {[string map {\\ {}} [$i getName]] eq $iname} { set inst $i; break } }
    }
    if {$inst eq "NULL" || ![[$inst getMaster] isBlock]} { error "OT_CCT: hard child $iname not found" }
    set cit {}
    foreach it [$inst getITerms] {
      if {[[$it getMTerm] getSigType] eq "CLOCK" && [$it getNet] ne "NULL"} { lappend cit $it }
    }
    if {[llength $cit] != 1} { error "OT_CCT: $iname has [llength $cit] connected clock pins (one expected)" }
    set it [lindex $cit 0]
    set mterm [[$it getMTerm] getName]
    set p [get_pins -quiet "[$inst getName]/$mterm"]
    if {[llength $p] != 1} { error "OT_CCT: $iname/$mterm not unique in STA" }
    set clks [get_property $p clocks]
    if {[llength $clks] != 1} { error "OT_CCT: $iname/$mterm has [llength $clks] clocks (one root expected)" }
    set clk [lindex $clks 0]
    set cell [get_cells -of_objects $p]
    set soft {}
    foreach sp [all_registers -clock $clk -clock_pins] {
      set sc [get_cells -quiet -of_objects $sp]
      if {[llength $sc]} {
        set sm [[ord::get_db] findMaster [get_property $sc ref_name]]
        if {$sm ne "NULL" && [$sm isBlock]} continue
      }
      lappend soft $sp
    }
    # per scene: corner, child range, soft range, pin arrival (a scene without propagated arrivals is skipped)
    set sc {}; set d {}
    foreach s [ot_cct_scenes $p] {
      set a0 [ot_cct_arr $p $s]
      if {$a0 eq ""} continue
      set corner [ot_cct_corner $cell $s]
      if {![dict exists $ranges $corner]} { error "OT_CCT: $iname has no $corner insertion range" }
      lassign [dict get $ranges $corner] cmin cmax
      set smin ""; set smax ""; set ns 0
      foreach sp $soft {
        set a [ot_cct_arr $sp $s]
        if {$a eq ""} continue
        if {$smin eq "" || $a < $smin} { set smin $a }
        if {$smax eq "" || $a > $smax} { set smax $a }
        incr ns
      }
      if {!$ns} continue
      dict set sc $s [list $corner $cmin $cmax $smin $smax]
      dict set d $s $a0
      puts [format "OT_CCT %s(%s) %s/%s root %s soft n=%d %.1f..%.1f child %.1f+(%.1f..%.1f) pair %.1f" \
        $s $corner $iname $mterm [get_full_name $clk] $ns $smin $smax $a0 $cmin $cmax \
        [expr {max($a0 + $cmax - $smin, $smax - $a0 - $cmin)}]]
    }
    if {![dict size $sc]} { error "OT_CCT: root [get_full_name $clk] of $iname has no scene with soft + pin arrivals" }
    set loc [$it getAvgXY]
    set x [lindex $loc 1]; set y [lindex $loc 2]
    if {![lindex $loc 0]} { set bb [$inst getBBox]; set x [$bb xMin]; set y [$bb yMin] }
    set r [dict create it $it iname $iname mterm $mterm pin $p x $x y $y n 0 last {} made {} sc $sc d $d rung 0 active 1 steps {}]
    dict set r w [ot_cct_worst $r]
    dict set r w0 [dict get $r w]
    lappend recs $r
  }
  set nr [llength $recs]
  set round 0
  while 1 {
    set any 0
    for {set i 0} {$i < $nr} {incr i} {
      set r [lindex $recs $i]
      if {![dict get $r active]} continue
      if {[dict get $r n] >= $lim} { dict set r active 0; lset recs $i $r; continue }
      set any 1
      lassign [lindex $ladder [dict get $r rung]] nm bm ain aout
      lset recs $i [ot_cct_insert $block $bm $ain $aout $r]
    }
    if {!$any} break
    estimate_parasitics -placement
    incr round
    for {set i 0} {$i < $nr} {incr i} {
      set r [lindex $recs $i]
      if {![dict get $r active] || ![llength [dict get $r last]]} continue
      set r [ot_cct_measure $r]
      set w [ot_cct_worst $r]
      set nm [lindex [lindex $ladder [dict get $r rung]] 0]
      if {$w <= [dict get $r w] - $gain} {
        dict set r w $w
        dict lappend r steps $nm
        puts [format "OT_CCT %s/%s keep %s n=%d worst pair %.1f" [dict get $r iname] [dict get $r mterm] $nm [dict get $r n] $w]
      } else {
        puts [format "OT_CCT %s/%s drop %s (worst pair %.1f vs %.1f)" [dict get $r iname] [dict get $r mterm] $nm $w [dict get $r w]]
        set r [ot_cct_remove_last $r]
        dict set r rung [expr {[dict get $r rung] + 1}]
        if {[dict get $r rung] >= [llength $ladder]} { dict set r active 0 }
        dict set r redo 1
      }
      dict set r last {}
      lset recs $i $r
    }
    # a removed step restores the previous arrivals: re-measure those records on the restored netlist next round
    set redo 0
    foreach r $recs { if {[dict exists $r redo]} { set redo 1 } }
    if {$redo} {
      estimate_parasitics -placement
      for {set i 0} {$i < $nr} {incr i} {
        set r [lindex $recs $i]
        if {![dict exists $r redo]} continue
        set r [ot_cct_measure $r]
        dict unset r redo
        lset recs $i $r
      }
    }
  }
  set tapped 0
  foreach r $recs {
    dict with r {
      if {[llength $made]} {
        if {[info exists ::env(OT_PG_STRICT)] && $::env(OT_PG_STRICT) eq "1"} {
          set pg_instances {}
          foreach o $made {if {[$o getObjectType] eq "dbInst"} {lappend pg_instances $o}}
          set pg_mapping [ot_pg_prepare_targets [ord::get_db_block] $pg_instances]
          foreach o $pg_instances {ot_pg_bind_before_protect $pg_mapping $o}
        } elseif {[llength [info procs ot_pg_standard_bind]]} {
          ot_pg_standard_bind child_centre_tap
        }
        foreach o $made { $o setDoNotTouch 1 }
        incr tapped
      }
      set txt {}
      dict for {s v} $sc {
        lassign $v corner cmin cmax smin smax
        set a [dict get $d $s]
        lappend txt [format "%s(%s) pin %.1f child %.1f..%.1f soft %.1f..%.1f pair %.1f" $s $corner $a [expr {$a + $cmin}] \
          [expr {$a + $cmax}] $smin $smax [expr {max($a + $cmax - $smin, $smax - $a - $cmin)}]]
      }
      puts [format "OT_CCT DONE %s/%s buffers=%d steps={%s} worst %.1f -> %.1f | %s" $iname $mterm $n $steps $w0 $w [join $txt " | "]]
    }
  }
  if {$tapped} { detailed_placement }
  estimate_parasitics -placement
  ot_cct_restore_modes $propagation_changes
  puts "OT_CCT centred $nr hard-child clock pins ($tapped tapped, $round parasitics rounds, minimax over scenes)"
}
if {[info procs clock_tree_synthesis] ne "" && [info procs ot_cct_cts_orig] eq ""} {
  rename clock_tree_synthesis ot_cct_cts_orig
  proc clock_tree_synthesis {args} {
    ot_cct_cts_orig {*}$args
    ot_cct_tap
  }
}
