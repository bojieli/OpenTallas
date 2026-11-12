# PRE_GLOBAL_ROUTE hook (FT-HOP-M2-WIRE, GEN-CLASS-1 2026-11-12, COORD-approved plan (1)): repeater pitch on the
# feedthrough-station HOP nets only, after the flow's own post-GRT repair_design.
# Why: HEAD hd_spn_wshim_tx HB4 failed sign-off DRV on 125 TT max-slew pins (466-572 ps vs 320); 120 of them are
# fanout-1 ~200-um wires from a repair BUFx3 to the next ft-link station input (u_ft_link_s0 INVx1 /A, u_ft_link_s2
# q[k] DFF /D) that GRT itself put on M2 (route.guide: one 200-um M2 segment).  repair_design saw them in limit on
# layer-average RC; the M2 RC of the detailed route did not.  This OpenROAD (26Q3-1510) has no per-net layer range,
# so the slew is bounded by repeater pitch: a second repair_design -max_wire_length OT_FT_MAXWIRE_UM (same SLEW/CAP
# margins) on the ft hop nets, every other net temporarily dont_touch (restored right after; nets already dont_touch
# are left alone).  Buffers only, 0 cycles.  Hop net = a signal net with at least one ft-station pin (instance name
# u_ft_* at any hierarchy level, e.g. u_bound.u_ft_ft12_o_4/...) whose other pins are ft-station pins, repeaters
# (BUF*/INV*/HB* masters: the repair chain of the hop, wherever repair_design named it) or ports, and pin bbox HPWL >
# OT_FT_MAXWIRE_UM.
# OT_FT_MAXWIRE_UM unset / 0 = off.  Composes with grt_maxwire.tcl and the GRT183 resume wrapper (same inner target).
if {![info exists ::env(OT_FT_MAXWIRE_UM)] || $::env(OT_FT_MAXWIRE_UM) eq "" || $::env(OT_FT_MAXWIRE_UM) == 0} { return }

proc ot_ft_hop_nets {lim_um} {
  set blk [ord::get_db_block]
  set dbu [$blk getDbUnitsPerMicron]
  set out {}
  foreach net [$blk getNets] {
    if {[$net getSigType] ne "SIGNAL" || [$net isSpecial]} continue
    set its [$net getITerms]
    set bts [$net getBTerms]
    if {[llength $its] + [llength $bts] < 2} continue
    set ok 1; set ft 0; set xs {}; set ys {}
    foreach it $its {
      set inst [$it getInst]
      if {[regexp {(^|[./])u_ft_} [$inst getName]]} {
        set ft 1
      } elseif {![regexp {^(BUF|INV|HB)} [[$inst getMaster] getName]]} {
        set ok 0; break
      }
      lassign [$inst getLocation] x y; lappend xs $x; lappend ys $y
    }
    if {!$ok || !$ft} continue
    foreach bt $bts {
      set bp [lindex [$bt getBPins] 0]
      if {$bp eq ""} continue
      set b [$bp getBBox]; lappend xs [$b xMin]; lappend ys [$b yMin]
    }
    set xs [lsort -integer $xs]; set ys [lsort -integer $ys]
    set hpwl [expr {double([lindex $xs end] - [lindex $xs 0] + [lindex $ys end] - [lindex $ys 0]) / $dbu}]
    if {$hpwl > $lim_um} { lappend out $net }
  }
  return $out
}

proc ot_ft_hop_pass {} {
  set lim $::env(OT_FT_MAXWIRE_UM)
  set blk [ord::get_db_block]
  set hops [ot_ft_hop_nets $lim]
  if {![llength $hops]} { puts "OT_FT_MAXWIRE: 0 ft hop nets over $lim um"; return }
  set keep [dict create]
  foreach n $hops { dict set keep [$n getId] 1 }
  set masked {}
  foreach n [$blk getNets] {
    if {[dict exists $keep [$n getId]] || [$n isDoNotTouch]} continue
    $n setDoNotTouch 1; lappend masked $n
  }
  set args [list -max_wire_length $lim]
  if {[info exists ::env(CAP_MARGIN)] && $::env(CAP_MARGIN) ne ""} { lappend args -cap_margin $::env(CAP_MARGIN) }
  if {[info exists ::env(SLEW_MARGIN)] && $::env(SLEW_MARGIN) ne ""} { lappend args -slew_margin $::env(SLEW_MARGIN) }
  if {[info exists ::env(MATCH_CELL_FOOTPRINT)] && $::env(MATCH_CELL_FOOTPRINT)} { lappend args -match_cell_footprint }
  set n0 [sta::network_leaf_instance_count]
  puts "OT_FT_MAXWIRE repair_design $args on [llength $hops] ft hop nets ([llength $masked] other nets dont_touch)"
  set rc [catch {log_cmd repair_design {*}$args} err opts]
  foreach n $masked { $n setDoNotTouch 0 }
  puts "OT_FT_MAXWIRE leaf instances $n0 -> [sta::network_leaf_instance_count]"
  if {$rc} { return -options $opts $err }
}

# grt_maxwire.tcl (OT_MAXWIRE_UM, S81 slice_station 62 / core 80-450) REPLACES repair_design_helper with one whole-design
# repair_design -max_wire_length and never calls the helper it renamed, so a hook below it (ot_g183_orig_) is dead
# there (t45 proof 11-12: "armed", never ran).  A design-wide limit <= ours already bounds every hop: say so, add nothing.
# A larger one: wrap the outermost helper, so the pass runs after that repair.
if {[info exists ::env(OT_MAXWIRE_UM)] && $::env(OT_MAXWIRE_UM) ne "" && $::env(OT_MAXWIRE_UM) > 0
    && $::env(OT_MAXWIRE_UM) <= $::env(OT_FT_MAXWIRE_UM)} {
  puts "OT_FT_MAXWIRE covered: OT_MAXWIRE_UM $::env(OT_MAXWIRE_UM) <= $::env(OT_FT_MAXWIRE_UM) um bounds every net; no ft hop pass"
  return
}
set ot_ftmw_target repair_design_helper
if {[info procs ot_orig_repair_design_helper] eq "" && [llength [info commands ot_g183_orig_repair_design_helper]]} {
  set ot_ftmw_target ot_g183_orig_repair_design_helper
}
if {[info procs $ot_ftmw_target] eq ""} { error "ft_hop_maxwire.tcl: $ot_ftmw_target not defined (flow scripts changed)" }
if {[info procs ot_ftmw_inner_repair_design_helper] eq ""} {
  rename $ot_ftmw_target ot_ftmw_inner_repair_design_helper
  proc $ot_ftmw_target {args} {
    ot_ftmw_inner_repair_design_helper {*}$args
    ot_ft_hop_pass
  }
  puts "OT_FT_MAXWIRE armed on $ot_ftmw_target (limit $::env(OT_FT_MAXWIRE_UM) um)"
}
