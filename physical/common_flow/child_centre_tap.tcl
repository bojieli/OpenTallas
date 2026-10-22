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
proc ot_cct_arr {pin} {
  # propagated-clock arrival at a clock pin (same tag read as landed_raw_tap ot_lrt_wire): rising, else falling
  sta::worst_slack_cmd max
  set scene [get_property [sta::cmd_scene] name]
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
proc ot_cct_corner {cell} {
  # the corner of the arrivals ot_cct_arr reads = the command scene's: OT_HOLD_MM sessions name them WC (mode ss) /
  # BC (mode ff); a single-scene session is the corner of its loaded library
  set sc [string tolower [get_property [sta::cmd_scene] name]]
  if {[regexp {^(wc|ss|slow|max)} $sc]} { return ss }
  if {[regexp {^(bc|ff|fast|min)} $sc]} { return ff }
  if {[regexp {^(tt|typ)} $sc]} { return tt }
  foreach lc [get_lib_cells -quiet -of_objects $cell] {
    if {[regexp -nocase {_(tt|ff|ss)[/_.]} [get_full_name $lc] -> c]} { return [string tolower $c] }
    if {[regexp -nocase {_(tt|ff|ss)$} [get_full_name $lc] -> c]} { return [string tolower $c] }
  }
  foreach lib [get_libs -quiet *] {
    if {[regexp -nocase {_(tt|ff|ss)(?:_|$)} [get_full_name $lib] -> c]} { return [string tolower $c] }
  }
  error "OT_CCT: no corner for the loaded library of [get_full_name $cell]"
}
proc ot_cct_tap {} {
  if {![info exists ::ot_cct_children] || ![dict size $::ot_cct_children]} return
  if {[info exists ::env(OT_PG_STRICT)] && $::env(OT_PG_STRICT) eq "1"} {ot_pg_require_cts_placement_or_empty_context}
  set block [ord::get_db_block]
  set bufname [expr {[info exists ::env(OT_CCT_BUF)] ? $::env(OT_CCT_BUF) : "BUFx4_ASAP7_75t_R"}]
  set lim [expr {[info exists ::env(OT_CCT_MAX)] ? $::env(OT_CCT_MAX) : 24}]
  set tol [expr {[info exists ::env(OT_CCT_TOL)] ? $::env(OT_CCT_TOL) : 4.0}]
  set bm [[ord::get_db] findMaster $bufname]
  if {$bm eq "NULL"} { error "OT_CCT: buffer master $bufname missing" }
  set ain ""; set aout ""
  foreach mt [$bm getMTerms] {
    if {[$mt getSigType] in {POWER GROUND}} continue
    if {[$mt getIoType] eq "INPUT"} { set ain [$mt getName] } elseif {[$mt getIoType] eq "OUTPUT"} { set aout [$mt getName] }
  }
  set ideal {}
  foreach c [all_clocks] { if {![get_property $c is_propagated]} { lappend ideal $c } }
  if {[llength $ideal]} { set_propagated_clock $ideal }
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
    set corner [ot_cct_corner [get_cells -of_objects $p]]
    if {![dict exists $ranges $corner]} { error "OT_CCT: $iname has no $corner insertion range" }
    lassign [dict get $ranges $corner] cmin cmax
    # soft registers of this root: every register clock pin of the clock except hard-child pins
    set smin ""; set smax ""; set ns 0
    foreach sp [all_registers -clock $clk -clock_pins] {
      set sc [get_cells -quiet -of_objects $sp]
      if {[llength $sc]} {
        set sm [[ord::get_db] findMaster [get_property $sc ref_name]]
        if {$sm ne "NULL" && [$sm isBlock]} continue
      }
      set a [ot_cct_arr $sp]
      if {$a eq ""} continue
      if {$smin eq "" || $a < $smin} { set smin $a }
      if {$smax eq "" || $a > $smax} { set smax $a }
      incr ns
    }
    if {!$ns} { error "OT_CCT: root [get_full_name $clk] of $iname has no soft register arrival" }
    set a0 [ot_cct_arr $p]
    if {$a0 eq ""} { error "OT_CCT: no propagated clock arrival on $iname/$mterm" }
    set want [expr {($smin + $smax) / 2.0 - ($cmin + $cmax) / 2.0}]
    set loc [$it getAvgXY]
    set x [lindex $loc 1]; set y [lindex $loc 2]
    if {![lindex $loc 0]} { set bb [$inst getBBox]; set x [$bb xMin]; set y [$bb yMin] }
    puts [format "OT_CCT %s %s/%s root %s soft n=%d %.1f..%.1f child %.1f+(%.1f..%.1f) -> pin target %.1f (now %.1f)" \
      $corner $iname $mterm [get_full_name $clk] $ns $smin $smax $a0 $cmin $cmax $want $a0]
    lappend recs [dict create it $it iname $iname mterm $mterm pin $p corner $corner want $want x $x y $y n 0 prev "" \
      d $a0 last {} made {} active [expr {$a0 < $want - $tol}] smin $smin smax $smax cmin $cmin cmax $cmax]
  }
  set nr [llength $recs]
  set round 0
  while 1 {
    set any 0
    for {set i 0} {$i < $nr} {incr i} {
      set r [lindex $recs $i]
      if {![dict get $r active]} continue
      set any 1
      dict with r {
        set prev $d
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
      lset recs $i $r
    }
    if {!$any} break
    estimate_parasitics -placement
    incr round
    for {set i 0} {$i < $nr} {incr i} {
      set r [lindex $recs $i]
      if {![dict get $r active]} continue
      dict with r {
        set d [ot_cct_arr $pin]
        if {$d eq ""} { error "OT_CCT: $iname/$mterm lost its clock arrival" }
        puts [format "OT_CCT %s %s/%s %s buffers=%d pin=%.1f target=%.1f" $corner $iname $mterm $bufname $n $d $want]
        if {$d - $prev < 0.5} { error "OT_CCT: $iname/$mterm: a buffer adds no delay" }
        if {$d >= $want || $n >= $lim} { set active 0 }
      }
      lset recs $i $r
    }
  }
  # the last buffer overshoots by < one buffer delay: drop it when n-1 buffers were nearer the target
  set dropped {}
  for {set i 0} {$i < $nr} {incr i} {
    set r [lindex $recs $i]
    dict with r {
      if {$n > 0 && $d < $want - $tol} { error "OT_CCT: $iname/$mterm: $lim buffers reach [format %.1f $d] < target [format %.1f $want]" }
      if {$n > 0 && $prev ne "" && $want - $prev < $d - $want} {
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
        lappend dropped $i
      }
    }
    lset recs $i $r
  }
  if {[llength $dropped]} {
    estimate_parasitics -placement
    foreach i $dropped {
      set r [lindex $recs $i]
      dict with r { set d [ot_cct_arr $pin] }
      lset recs $i $r
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
      set lo [expr {min($d + $cmin, $smin)}]; set hi [expr {max($d + $cmax, $smax)}]
      set pair [expr {max($d + $cmax - $smin, $smax - $d - $cmin)}]
      puts [format "OT_CCT DONE %s %s/%s buffers=%d pin=%.1f target=%.1f residual=%.1f child %.1f..%.1f soft %.1f..%.1f pair %.1f" \
        $corner $iname $mterm $n $d $want [expr {$d - $want}] [expr {$d + $cmin}] [expr {$d + $cmax}] $smin $smax $pair]
    }
  }
  if {$tapped} { detailed_placement }
  estimate_parasitics -placement
  if {[llength $ideal]} { unset_propagated_clock $ideal }
  puts "OT_CCT centred $nr hard-child clock pins ($tapped tapped, $round parasitics rounds)"
}
if {[info procs clock_tree_synthesis] ne "" && [info procs ot_cct_cts_orig] eq ""} {
  rename clock_tree_synthesis ot_cct_cts_orig
  proc clock_tree_synthesis {args} {
    ot_cct_cts_orig {*}$args
    ot_cct_tap
  }
}
