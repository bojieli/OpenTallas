# GENERATED-COPY of tools/die_plan/grt_pre.tcl (PRE_GLOBAL_ROUTE hook, FLOW 2026-10-25): FF-only GRT step binds the IO
# virtual clock to the FF insertion (vclk_corner.tcl, OT_VCLK_CORNER=ff from run_kit.sh) before the hold repair;
# optional repeater pitch (grt_maxwire.tcl, OT_MAXWIRE_UM).
set gp_dir [file dirname [file normalize [info script]]]
# KW-FIX-16 11-05: a GRT resumed from 4_cts.odb takes the signal layer range from MIN/MAX_ROUTING_LAYER (grt_layers.tcl)
if {[file exists [file join $gp_dir grt_layers.tcl]]} { source [file join $gp_dir grt_layers.tcl] }
source [file join $gp_dir vclk_corner.tcl]
if {[info exists ::env(OT_MAXWIRE_UM)] && $::env(OT_MAXWIRE_UM) ne ""} { source [file join $gp_dir grt_maxwire.tcl] }
# FT-HOP-M2-WIRE 11-12: repeater pitch on the ft-station hop nets only (ft_hop_maxwire.tcl, OT_FT_MAXWIRE_UM)
if {[info exists ::env(OT_FT_MAXWIRE_UM)] && $::env(OT_FT_MAXWIRE_UM) ne "" && [file exists [file join $gp_dir ft_hop_maxwire.tcl]]} { source [file join $gp_dir ft_hop_maxwire.tcl] }
# FLOW-23 11-02 HOLD-GUARD-GRT: progress/time bound for the single-mode GRT hold repair (hold_guard_grt.tcl; OT_HOLD_GUARD=0 off)
if {[file exists [file join $gp_dir hold_guard_grt.tcl]]} { source [file join $gp_dir hold_guard_grt.tcl] }
# DIE-HBM-97 11-09 HOPLATCH-HOLD (COORD; qmca_vSR3: 85 hop latches re-hung on their capture tap, setup 0 viol, but FF hold
# -22.62 / 33 on u_rrl_* -> u_fl_rst_*: GRT hold repair closed to +0.27 at margin 0, routed RC took 22.6 ps): a hop latch
# matched by OT_HOP_LATCH_CAPTURE_TAP may sit on its CAPTURE tap, so its launch -> latch hop crosses the tap boundary.
# Safe by construction: its clock pin gets -hold uncertainty OT_HOP_LATCH_HOLD_PS (default 30) for the GRT hold repair
# only, so the repair pads that hop past the GRT -> routed RC shift.  grt_post.tcl removes it before 5_1_grt.sdc is
# written: sign-off constraints, margins and acceptance are unchanged.  OT_HOP_LATCH_HOLD_PS=0 = off.
proc ot_hop_latch_hold_pins {blk res} {
  set out {}
  foreach i [$blk getInsts] {
    set nm [$i getName]
    if {![regexp {(^|[./])u_fl_} $nm]} continue
    set hit 0
    foreach re $res { if {[regexp -- $re $nm]} { set hit 1; break } }
    if {!$hit} continue
    foreach it [$i getITerms] {
      if {[[$it getMTerm] getName] eq "CLK" && [$it getNet] ne "NULL"} { lappend out "$nm/CLK"; break }
    }
  }
  return $out
}
set ::ot_hlh_pins {}
if {[info exists ::env(OT_HOP_LATCH_CAPTURE_TAP)] && [string trim $::env(OT_HOP_LATCH_CAPTURE_TAP)] ne ""} {
  set ot_hlh_ps [expr {[info exists ::env(OT_HOP_LATCH_HOLD_PS)] && $::env(OT_HOP_LATCH_HOLD_PS) ne "" ? $::env(OT_HOP_LATCH_HOLD_PS) : 30}]
  if {$ot_hlh_ps > 0} {
    set ot_hlh_u $ot_hlh_ps   ;# SDC / liberty time unit = 1 ps (gen_phys LIB_TIME_UNIT_PS)
    foreach ot_hlh_n [ot_hop_latch_hold_pins [ord::get_db_block] $::env(OT_HOP_LATCH_CAPTURE_TAP)] {
      set ot_hlh_p [sta::find_pin $ot_hlh_n]
      if {$ot_hlh_p eq "NULL" || $ot_hlh_p eq ""} continue
      set_clock_uncertainty -hold $ot_hlh_u $ot_hlh_p
      lappend ::ot_hlh_pins $ot_hlh_p
    }
    puts "OT_HOP_LATCH_HOLD [llength $::ot_hlh_pins] hop latch clock pins carry -hold uncertainty $ot_hlh_ps ps for the GRT hold repair"
  }
}
