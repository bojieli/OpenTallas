if {[info exists ::env(OT_PG_STRICT)] && $::env(OT_PG_STRICT) eq "1"} {
  set ot_pg_helper [file join [file dirname [info script]] native_pg_binding.tcl]
  if {[info exists ::env(OT_PG_HELPER)]} {set ot_pg_helper $::env(OT_PG_HELPER)} elseif {![file exists $ot_pg_helper]} {set ot_pg_helper /src/physical/common_flow/native_pg_binding.tcl}
  source $ot_pg_helper
  ot_pg_install_final_write_guard
  ot_pg_install_rc_observers
}
# landed_raw_tap.tcl (HF-4d 2026-10-19, coordinator option A for qfd_tt_ctlm_dv / h16c): post-CTS delay tap for the RAW
# SRAM clock pins of a hard child in a LANDED cluster (tools/ref_tile clock_entry_constraints.landed_raw_pins).
#
# The leaf (h16c ot_qfd_tt_ctlm_static_hr, hybrid_entries) signed off its direct SRAM entries ck_pm0/ck_pm1 CO-TIMED with
# the boundary flops of its CTS root ck_head (record sign-off: latency(ck_pm) = phi - wire, phi = R(ck_head) ~303 TT /
# 248 FF), i.e. the parent must deliver ck_pm R(ck_head) - w_leaf(ck_pm) LATER than ck_head (~288 ps TT).  TritonCTS
# cannot: every clock pin of a hard child goes to the root's MACRO tree and gets the same pin arrival (toy flow: CKP and
# CLK 88.9 ps both, skew -85 vs the required +85), whatever the ETM clock_tree_path says.  This hook runs right after
# clock_tree_synthesis (source it AFTER clock_entries.tcl, BEFORE the boundary wrapper that re-applies clock_entry.sdc,
# whose OT_LANDED RAW_PIN check is the verdict): per raw pin it measures the propagated pin arrivals of the raw pin and
# its co-timed pin on the same root and inserts a dont-touch chain of clock buffers in front of the raw pin until
# wire(raw) - wire(ref) reaches the record target of the loaded corner (+- one buffer).  Nothing else changes: no SDC
# latency, no ETM edit, no other net.  Fails closed when a pin, its co-timed pin, its arrival or the target is missing.
#
# Input (ref_tile pre_cts.tcl): ::ot_lrt_targets = dict {master/rawpin} {ref <pin> tt <ps> ff <ps> ss <ps>} with
# <ps> = R(ref).boundary.mean - w_leaf(raw).mean of that corner.  Env OT_LRT_BUF (default BUFx4_ASAP7_75t_R),
# OT_LRT_MAX (default 64 buffers per pin).
proc ot_lrt_wire {pin} {
  # same propagated-clock tag read as clock_entry_constraints ot_ce_clock_wire (a clock-only macro pin has no DATA
  # arrival); the rising pin transition, else the falling one
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
  if {$best eq ""} { error "OT_LRT: no propagated clock arrival on [get_full_name $pin]" }
  return $best
}
proc ot_lrt_corner {cell} {
  foreach lc [get_lib_cells -quiet -of_objects $cell] {
    if {[regexp -nocase {_(tt|ff|ss)[/_]} [get_full_name $lc] -> c]} { return [string tolower $c] }
  }
  error "OT_LRT: no corner for the loaded library of [get_full_name $cell]"
}
proc ot_lrt_tap {} {
  if {![info exists ::ot_lrt_targets] || ![dict size $::ot_lrt_targets]} return
  if {[info exists ::env(OT_PG_STRICT)] && $::env(OT_PG_STRICT) eq "1"} {ot_pg_require_cts_placement_or_empty_context}
  set block [ord::get_db_block]
  set bufname [expr {[info exists ::env(OT_LRT_BUF)] ? $::env(OT_LRT_BUF) : "BUFx4_ASAP7_75t_R"}]
  set lim [expr {[info exists ::env(OT_LRT_MAX)] ? $::env(OT_LRT_MAX) : 64}]
  set bm [[ord::get_db] findMaster $bufname]
  if {$bm eq "NULL"} { error "OT_LRT: buffer master $bufname missing" }
  set ain ""; set aout ""
  foreach mt [$bm getMTerms] {
    if {[$mt getSigType] in {POWER GROUND}} continue
    if {[$mt getIoType] eq "INPUT"} { set ain [$mt getName] } elseif {[$mt getIoType] eq "OUTPUT"} { set aout [$mt getName] }
  }
  # measure on propagated clocks (the CTS wrapper runs before the flow propagates them); restore ideal ones after
  set ideal {}
  foreach c [all_clocks] { if {![get_property $c is_propagated]} { lappend ideal $c } }
  if {[llength $ideal]} { set_propagated_clock $ideal }
  # BATCHED (L2H-PGVM 2026-10-19, Gate-Rule neutral): gate_lg2 of hbm_su_pgslice_lg_light_d4g stalled 2 x 14400 s here --
  # the per-pin loop ran one full-design estimate_parasitics per buffer per pin (~40 s on 210k cells, ~1,000 rounds).
  # Same per-pin rule, targets, limits, errors and final overshoot drop; the pins are advanced together, one buffer per
  # unfinished pin per round, with ONE estimate_parasitics per round (rounds = the longest chain, not the sum).
  set recs {}
  foreach inst [$block getInsts] {
    set master [[$inst getMaster] getName]
    foreach it [$inst getITerms] {
      set key "$master/[[$it getMTerm] getName]"
      if {![dict exists $::ot_lrt_targets $key]} continue
      set t [dict get $::ot_lrt_targets $key]
      set iname [$inst getName]
      set refit [$inst findITerm [dict get $t ref]]
      if {$refit eq "NULL" || [$refit getNet] eq "NULL" || [$it getNet] eq "NULL"} {
        error "OT_LRT: $iname: raw pin or its co-timed pin [dict get $t ref] unconnected"
      }
      set cell [get_cells -quiet $iname]
      if {[llength $cell] != 1} { error "OT_LRT: $iname: no unique STA cell" }
      set rpin {}; set fpin {}
      foreach p [get_pins -of_objects $cell] {
        set lp [get_property $p lib_pin_name]
        if {$lp eq [[$it getMTerm] getName]} { lappend rpin $p } elseif {$lp eq [dict get $t ref]} { lappend fpin $p }
      }
      if {[llength $rpin] != 1 || [llength $fpin] != 1} { error "OT_LRT: $iname: pins not unique in STA" }
      set corner [ot_lrt_corner $cell]
      set loc [$it getAvgXY]
      set x [lindex $loc 1]; set y [lindex $loc 2]
      if {![lindex $loc 0]} { set bb [$inst getBBox]; set x [$bb xMin]; set y [$bb yMin] }
      lappend recs [dict create it $it iname $iname mterm [[$it getMTerm] getName] rpin $rpin fpin $fpin corner $corner \
        want [dict get $t $corner] x $x y $y n 0 prev "" d 0 last {} made {} active 1]
    }
  }
  # ANCHOR (L2H-PGVM 2026-10-19, gate_lg3): the targets are relative to a co-timed pin that is never tapped (clk_ws of
  # the bank6 child), but a buffer can only ADD delay: when another pin of the same child already arrives later than
  # its target (u_bk_r*_1/clk_rd raw-ref 190 vs 66 -> +124 ps), the whole child is mis-timed against the verdict's
  # CTS-root pin.  Per (child, ref) group: a_p = propagated pin arrival, t_p = target (t_ref = 0); common offset
  # C = max(a_ref, max_p(a_p - t_p)); every pin, the ref included, is tapped to its ABSOLUTE goal C + t_p.  Same per-pin
  # chain rule, limit, errors and overshoot drop; the relative residual (vs the ref) is what is reported.
  estimate_parasitics -placement
  set groups [dict create]
  set nr0 [llength $recs]
  for {set i 0} {$i < $nr0} {incr i} {
    set r [lindex $recs $i]
    set g "[dict get $r iname]|[get_full_name [dict get $r fpin]]"
    dict lappend groups $g $i
  }
  dict for {g idx} $groups {
    set r0 [lindex $recs [lindex $idx 0]]
    set fpin [dict get $r0 fpin]
    set aref [ot_lrt_wire $fpin]
    set c $aref
    foreach i $idx {
      set r [lindex $recs $i]
      set a [ot_lrt_wire [dict get $r rpin]]
      if {$a - [dict get $r want] > $c} { set c [expr {$a - [dict get $r want]}] }
    }
    foreach i $idx {
      set r [lindex $recs $i]
      dict set r goal [expr {$c + [dict get $r want]}]
      dict set r refpin $fpin
      lset recs $i $r
    }
    if {$c - $aref >= 0.5} {
      # the ref itself must arrive later: tap it as an ordinary pin of the group (want 0 relative to itself)
      set inst [$block findInst [dict get $r0 iname]]
      set rlib [get_property $fpin lib_pin_name]
      set fit [$inst findITerm $rlib]
      if {$fit eq "NULL" || [$fit getNet] eq "NULL"} { error "OT_LRT: [dict get $r0 iname]/$rlib: anchor pin unconnected" }
      lappend recs [dict create it $fit iname [dict get $r0 iname] mterm $rlib rpin $fpin fpin $fpin \
        corner [dict get $r0 corner] want 0.0 goal $c refpin $fpin x [dict get $r0 x] y [dict get $r0 y] n 0 prev "" d 0 \
        last {} made {} active 1 anchor 1]
      puts [format "OT_LRT ANCHOR %s/%s +%.1f ps (a pin of the child arrives later than its target)" [dict get $r0 iname] $rlib [expr {$c - $aref}]]
    }
  }
  set nr [llength $recs]
  set round 0
  set first 1
  while 1 {
    set any 0
    for {set i 0} {$i < $nr} {incr i} { if {[dict get [lindex $recs $i] active]} { set any 1; break } }
    if {!$any} break
    if {!$first} { estimate_parasitics -placement }
    set first 0
    incr round
    for {set i 0} {$i < $nr} {incr i} {
      set r [lindex $recs $i]
      if {![dict get $r active]} continue
      dict with r {
        set d [ot_lrt_wire $rpin]
        puts [format "OT_LRT %s %s/%s %s buffers=%d arrival=%.1f goal=%.1f" $corner $iname $mterm $bufname $n $d $goal]
        if {$prev ne "" && $d - $prev < 0.5} { error "OT_LRT: $iname/$mterm: a buffer adds no delay" }
        if {$d >= $goal - 0.05 || $n >= $lim} {
          set active 0
        } else {
          set prev $d
          # one more buffer in front of the pin: (net) -> buf -> new net -> pin
          set old [$it getNet]
          set b [odb::dbInst_create $block $bm "ot_lrt_${iname}_${mterm}_$n"]
          if {$b eq "NULL"} { error "OT_LRT: cannot create tap buffer" }
          $b setLocation [expr {int($x)}] [expr {int($y)}]
          $b setPlacementStatus PLACED
          set nn [odb::dbNet_create $block "ot_lrt_n_${iname}_${mterm}_$n"]
          $nn setSigType CLOCK
          $it disconnect
          [$b findITerm $ain] connect $old
          [$b findITerm $aout] connect $nn
          $it connect $nn
          # Bind before the next placement estimate and arrival measurement.
          if {[info exists ::env(OT_PG_STRICT)] && $::env(OT_PG_STRICT) eq "1"} {ot_pg_bind_before_protect [ot_pg_prepare_targets $block [list $b]] $b}
          set last [list $b $nn $old]
          lappend made $b $nn
          incr n
        }
      }
      lset recs $i $r
    }
  }
  puts "OT_LRT batched: $nr raw pins, $round parasitics rounds"
  # the last buffer overshoots by < one buffer delay: drop it when n-1 buffers were nearer the goal
  set dropped {}
  for {set i 0} {$i < $nr} {incr i} {
    set r [lindex $recs $i]
    dict with r {
      if {$d < $goal - 0.05} { error "OT_LRT: $iname/$mterm: $lim buffers reach [format %.1f $d] < goal [format %.1f $goal]" }
      if {$n > 0 && $prev ne "" && $goal - $prev < $d - $goal} {
        lassign $last b nn old
        set made [lrange $made 0 end-2]
        $it disconnect
        odb::dbInst_destroy $b
        odb::dbNet_destroy $nn
        $it connect $old
        incr n -1
        lappend dropped $i
      }
    }
    lset recs $i $r
  }
  # final relative measure (raw - ref, what the OT_LANDED verdict judges)
  estimate_parasitics -placement
  for {set i 0} {$i < $nr} {incr i} {
    set r [lindex $recs $i]
    dict with r { set d [expr {[ot_lrt_wire $rpin] - [ot_lrt_wire $refpin]}] }
    lset recs $i $r
  }
  set done 0
  foreach r $recs {
    dict with r {
      # the chain is final: keep it out of later resizing / buffering / net repair
      if {[expr {[info exists ::env(OT_PG_STRICT)] && $::env(OT_PG_STRICT) eq "1"}]} {
        set pg_instances {}
        foreach o $made {if {[$o getObjectType] eq "dbInst"} {lappend pg_instances $o}}
        set pg_mapping [ot_pg_prepare_targets [ord::get_db_block] $pg_instances]
        foreach o $pg_instances {ot_pg_bind_before_protect $pg_mapping $o}
      }
      foreach o $made { $o setDoNotTouch 1 }
      puts [format "OT_LRT DONE %s %s/%s buffers=%d raw-ref=%.1f target=%.1f residual=%.1f%s" $corner $iname $mterm $n $d $want [expr {$d - $want}] [expr {[dict exists $r anchor] ? " (anchor)" : ""}]]
    }
    incr done
  }
  if {!$done} { error "OT_LRT: no raw child clock pin found for [dict keys $::ot_lrt_targets]" }
  detailed_placement
  estimate_parasitics -placement
  if {[llength $ideal]} { unset_propagated_clock $ideal }
  puts "OT_LRT tapped $done raw child clock pins"
}
if {[info procs clock_tree_synthesis] ne "" && [info procs ot_lrt_cts_orig] eq ""} {
  rename clock_tree_synthesis ot_lrt_cts_orig
  proc clock_tree_synthesis {args} {
    ot_lrt_cts_orig {*}$args
    ot_lrt_tap
  }
}
