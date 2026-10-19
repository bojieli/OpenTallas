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
  set done 0
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
      set want [dict get $t $corner]
      set loc [$it getAvgXY]
      set x [lindex $loc 1]; set y [lindex $loc 2]
      if {![lindex $loc 0]} { set bb [$inst getBBox]; set x [$bb xMin]; set y [$bb yMin] }
      set n 0; set prev ""; set last {}; set made {}
      while 1 {
        estimate_parasitics -placement
        set d [expr {[ot_lrt_wire $rpin] - [ot_lrt_wire $fpin]}]
        puts [format "OT_LRT %s %s/%s %s buffers=%d raw-ref=%.1f target=%.1f" $corner $iname [[$it getMTerm] getName] $bufname $n $d $want]
        if {$prev ne "" && $d - $prev < 0.5} { error "OT_LRT: $iname/[[$it getMTerm] getName]: a buffer adds no delay" }
        if {$d >= $want || $n >= $lim} break
        set prev $d
        # one more buffer in front of the raw pin: (net) -> buf -> new net -> raw pin
        set old [$it getNet]
        set b [odb::dbInst_create $block $bm "ot_lrt_${iname}_[[$it getMTerm] getName]_$n"]
        if {$b eq "NULL"} { error "OT_LRT: cannot create tap buffer" }
        $b setLocation [expr {int($x)}] [expr {int($y)}]
        $b setPlacementStatus PLACED
        set nn [odb::dbNet_create $block "ot_lrt_n_${iname}_[[$it getMTerm] getName]_$n"]
        $nn setSigType CLOCK
        $it disconnect
        [$b findITerm $ain] connect $old
        [$b findITerm $aout] connect $nn
        $it connect $nn
        set last [list $b $nn $old]
        lappend made $b $nn
        incr n
      }
      if {$d < $want} { error "OT_LRT: $iname/[[$it getMTerm] getName]: $lim buffers reach [format %.1f $d] < target $want" }
      # the last buffer overshoots by < one buffer delay: drop it when n-1 buffers were nearer the target
      if {$n > 0 && $prev ne "" && $want - $prev < $d - $want} {
        lassign $last b nn old
        set made [lrange $made 0 end-2]
        $it disconnect
        odb::dbInst_destroy $b
        odb::dbNet_destroy $nn
        $it connect $old
        incr n -1
        estimate_parasitics -placement
        set d [expr {[ot_lrt_wire $rpin] - [ot_lrt_wire $fpin]}]
      }
      # the chain is final: keep it out of later resizing / buffering / net repair
      foreach o $made { $o setDoNotTouch 1 }
      puts [format "OT_LRT DONE %s %s/%s buffers=%d raw-ref=%.1f target=%.1f residual=%.1f" $corner $iname [[$it getMTerm] getName] $n $d $want [expr {$d - $want}]]
      incr done
    }
  }
  if {!$done} { error "OT_LRT: no raw child clock pin found for [dict keys $::ot_lrt_targets]" }
  detailed_placement
  estimate_parasitics -placement
  if {[llength $ideal]} { unset_propagated_clock $ideal }
  puts "OT_LRT tapped $done raw child clock pins"
}
# MU-DQ-CTLMCLK 10-19 (COORD 0ke option a, opt-in ::ot_lrt_detach 1 from spec landed_raw_detach): TritonCTS puts every
# clock pin of a hard child into the root's macro tree and balances the root's registers against that tree; with the raw
# SRAM pins (ETM insertion ~15 ps) in it beside ck_head (~303 ps) the registers were NOT lifted to ck_head (qfd_tt_ctlm_dv
# gate f: soft-vs-h16c pair 416/356).  Detach every tapped raw pin before CTS (the tree sees ck_head only), reconnect it
# to the CTS-built net of its co-timed ref pin after CTS; ot_lrt_tap then delays it to the record offset from that net.
proc ot_lrt_detach {} {
  set out {}
  if {![info exists ::ot_lrt_detach] || !$::ot_lrt_detach || ![info exists ::ot_lrt_targets]} { return $out }
  foreach inst [[ord::get_db_block] getInsts] {
    set master [[$inst getMaster] getName]
    foreach it [$inst getITerms] {
      set key "$master/[[$it getMTerm] getName]"
      if {![dict exists $::ot_lrt_targets $key]} continue
      set refit [$inst findITerm [dict get $::ot_lrt_targets $key ref]]
      if {$refit eq "NULL" || [$it getNet] eq "NULL" || [$refit getNet] eq "NULL"} {
        error "OT_LRT: detach [$inst getName]/[[$it getMTerm] getName]: raw or ref pin unconnected"
      }
      if {[[$it getNet] getName] ne [[$refit getNet] getName]} {
        error "OT_LRT: detach [$inst getName]/[[$it getMTerm] getName]: not on the ref pin's net (nothing to re-drive from)"
      }
      lappend out [list $it $refit [[$it getNet] getName]]
      $it disconnect
      puts "OT_LRT DETACH [$inst getName]/[[$it getMTerm] getName] from [lindex $out end 2] for CTS (ref [dict get $::ot_lrt_targets $key ref])"
    }
  }
  if {![llength $out]} { error "OT_LRT: ::ot_lrt_detach set but no raw child clock pin found" }
  return $out
}
proc ot_lrt_reattach {det} {
  foreach d $det {
    lassign $d it refit oldname
    set rn [$refit getNet]
    if {$rn eq "NULL"} { error "OT_LRT: reattach: ref pin lost its net after CTS" }
    $it connect $rn
    puts "OT_LRT REATTACH [[$it getInst] getName]/[[$it getMTerm] getName] -> [$rn getName] (ref net after CTS; was $oldname)"
  }
}
if {[info procs clock_tree_synthesis] ne "" && [info procs ot_lrt_cts_orig] eq ""} {
  rename clock_tree_synthesis ot_lrt_cts_orig
  proc clock_tree_synthesis {args} {
    set det [ot_lrt_detach]
    ot_lrt_cts_orig {*}$args
    ot_lrt_reattach $det
    ot_lrt_tap
  }
}
