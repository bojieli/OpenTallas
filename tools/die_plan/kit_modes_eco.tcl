# GENERATED-COPY of tools/die_plan/kit_modes_eco.tcl (SIGNOFF-MODES-1 2026-10-27): per-mode guard for a warm post-route
# ECO hook (POST_GLOBAL_ROUTE of a do-route from the routed DB, 4_cts.sdc).  Same rule as HEAD-R17 head_eco_post.tcl:
#   two-corner ECO -> the orfs_hold_mm two-mode session must be active and synced (scene tc = TT setup, vclk 250 from
#   constraint.sdc; scene BC = FF hold, vclk_ff.sdc 202.5) before the ECO's own repair_timing calls; FF-only ECO -> the
#   vclk must carry OT_VCLK_FF.  Anything else errors (fail closed).  `kit_modes_eco_done` restores mode ss after.
proc kit_modes_vclk_latency {} {
  set vc {}
  foreach c [all_clocks] { if {![llength [get_property $c sources]]} { lappend vc $c } }
  if {[llength $vc] != 1} { error "KIT_MODES FAIL: expected one IO virtual clock, found [llength $vc]" }
  return [lindex $vc 0]
}
if {[info exists ::env(OT_HOLD_MM)] && $::env(OT_HOLD_MM) eq "1"} {
  if {![llength [info commands ot_mm_sync]] || ![info exists ::ot_mm_active] || !$::ot_mm_active} {
    error "KIT_MODES FAIL: OT_HOLD_MM=1 but no orfs_hold_mm two-mode session (container not patched with orfs_hold_mm.py)"
  }
  if {[info exists ::env(OT_VCLK_CORNER)] && $::env(OT_VCLK_CORNER) eq "ff"} {
    error "KIT_MODES FAIL: OT_VCLK_CORNER=ff in a two-mode session (FF latency in mode ss)"
  }
  if {[ot_mm_sc] ne "tc"} { error "KIT_MODES FAIL: setup scene [ot_mm_sc] is not tc" }
  ot_mm_sync
  if {![info exists ::ot_mm_synced] || !$::ot_mm_synced} { error "KIT_MODES FAIL: ot_mm_sync did not sync the FF mode" }
  puts [format "KIT_MODES eco per-mode: tc setup %.3f / BC hold %.3f ps" [ot_mm_ws max [ot_mm_sc]] [ot_mm_ws min BC]]
  proc kit_modes_eco_done {} { ot_mm_unsync; puts "KIT_MODES eco done (mode ss never carried the FF vclk)" }
} else {
  set km_cs [string tolower [expr {[info exists ::env(CORNERS)] ? $::env(CORNERS) : ""}]]
  if {[llength $km_cs] != 1 || [lindex $km_cs 0] ne "bc"} {
    error "KIT_MODES FAIL: single-mode ECO over corners '$km_cs' (two corners need OT_HOLD_MM=1, kit_modes.py stage)"
  }
  if {![info exists ::env(OT_VCLK_CORNER)] || $::env(OT_VCLK_CORNER) ne "ff"} {
    error "KIT_MODES FAIL: FF-only ECO without OT_VCLK_CORNER=ff (FF hold against the TT vclk)"
  }
  kit_modes_vclk_latency
  puts "KIT_MODES eco FF-only, vclk = OT_VCLK_FF $::env(OT_VCLK_FF)"
  proc kit_modes_eco_done {} {}
}
